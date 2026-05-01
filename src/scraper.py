"""쿠팡 검색 결과 스크래핑 모듈."""

from __future__ import annotations

import os
from pathlib import Path
import time
from dataclasses import dataclass, asdict
import re
from typing import List, Optional
from urllib.parse import quote

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.common.exceptions import InvalidSessionIdException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class KeywordResult:
    """키워드 1개에 대한 1페이지 분석 결과."""

    keyword: str
    total: int = 0
    rocket: int = 0
    seller_rocket: int = 0
    seller_delivery: int = 0
    seller_rocket_review_over_2000: int = 0
    seller_rocket_max_review_count: int = 0

    @property
    def rocket_ratio(self) -> float:
        return self.rocket / self.total if self.total else 0.0

    @property
    def seller_rocket_ratio(self) -> float:
        return self.seller_rocket / self.total if self.total else 0.0

    @property
    def seller_delivery_ratio(self) -> float:
        return self.seller_delivery / self.total if self.total else 0.0

    @property
    def rocket_ratio_pass(self) -> bool:
        return self.total > 0 and self.rocket_ratio <= 0.10

    @property
    def seller_rocket_review_pass(self) -> bool:
        return self.seller_rocket_review_over_2000 == 0

    @property
    def ttudung(self) -> str:
        pass_count = (
            int(self.rocket_ratio_pass)
            + int(self.seller_rocket_review_pass)
        )
        if pass_count == 2:
            return "넙덕"
        if pass_count == 1:
            return "뼈다구"
        return "돼지"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["rocket_ratio"] = round(self.rocket_ratio * 100, 1)
        data["seller_rocket_ratio"] = round(self.seller_rocket_ratio * 100, 1)
        data["seller_delivery_ratio"] = round(
            self.seller_delivery_ratio * 100,
            1,
        )
        data["rocket_ratio_pass"] = "합격" if self.rocket_ratio_pass else "불합격"
        data["seller_rocket_review_pass"] = (
            "합격" if self.seller_rocket_review_pass else "불합격"
        )
        data["ttudung"] = self.ttudung
        return data


class CoupangScraper:
    """쿠팡 키워드 검색 스크래퍼."""

    HOME_URL = "https://www.coupang.com/"
    BASE_URL = "https://www.coupang.com/np/search"
    PAGE_LOAD_WAIT = 3.5
    RESULT_WAIT_TIMEOUT = 40
    MAX_RETRY = 3
    PRODUCT_SELECTOR = "li.search-product, li[class*='ProductUnit']"
    SEARCH_INPUT_SELECTOR = (
        "input[name='q'], "
        "input#headerSearchKeyword, "
        "input[placeholder*='검색']"
    )

    def __init__(
        self,
        headless: bool = True,
        chrome_version: Optional[int] = None,
        profile_dir: Optional[str] = None,
    ) -> None:
        self.headless = headless
        self.chrome_version = (
            chrome_version
            or self._detect_chrome_major_version()
        )
        self.profile_dir = Path(
            profile_dir
            or os.getenv("COUPANG_CHROME_PROFILE_DIR")
            or self._default_profile_dir()
        )
        self._driver: Optional[uc.Chrome] = None

    @staticmethod
    def _default_profile_dir() -> Path:
        local_app_data = os.getenv("LOCALAPPDATA")
        if local_app_data:
            base_dir = Path(local_app_data)
        else:
            base_dir = Path.home() / "AppData" / "Local"

        return base_dir / "CoupangKeywordAnalyzer" / "chrome_profile"

    @staticmethod
    def _detect_chrome_major_version() -> Optional[int]:
        """설치된 Chrome의 메이저 버전을 감지한다 (Windows 기준)."""
        import os
        import re
        import subprocess

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(
                r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
            ),
        ]
        for path in chrome_paths:
            if not os.path.exists(path):
                continue
            try:
                out = subprocess.check_output(
                    [
                        "powershell",
                        "-Command",
                        f"(Get-Item '{path}').VersionInfo.ProductVersion",
                    ],
                    stderr=subprocess.DEVNULL,
                ).decode(errors="ignore")
                m = re.search(r"(\d+)\.\d+\.\d+\.\d+", out)
                if m:
                    return int(m.group(1))
            except Exception:
                continue
        return None

    def _build_driver(self) -> uc.Chrome:
        self.profile_dir.mkdir(parents=True, exist_ok=True)

        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--lang=ko-KR")
        options.add_argument("--window-size=1280,900")
        options.add_argument("--no-first-run")
        options.add_argument("--no-default-browser-check")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument(f"--user-data-dir={self.profile_dir}")
        options.add_argument(
            f"--profile-directory={os.getenv('COUPANG_CHROME_PROFILE_NAME', 'Default')}"
        )
        kwargs = {"options": options}
        if self.chrome_version:
            kwargs["version_main"] = self.chrome_version
        return uc.Chrome(**kwargs)

    def _ensure_driver(self) -> uc.Chrome:
        if self._driver is None:
            self._driver = self._build_driver()
        return self._driver

    def _reset_driver(self) -> uc.Chrome:
        self.close()
        return self._ensure_driver()

    def close(self) -> None:
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def __enter__(self) -> "CoupangScraper":
        self._ensure_driver()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def search(self, keyword: str) -> KeywordResult:
        """키워드 1개를 검색하고 1페이지 결과를 집계한다."""
        driver = self._ensure_driver()

        last_blocked = False
        for attempt in range(self.MAX_RETRY):
            try:
                self._run_search_attempt(driver, keyword, use_home_first=(attempt == 0))
            except InvalidSessionIdException:
                driver = self._reset_driver()
                continue

            # Akamai 챌린지 통과 + 검색 결과 로드까지 대기
            try:
                WebDriverWait(driver, self.RESULT_WAIT_TIMEOUT).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.PRODUCT_SELECTOR)
                    )
                )
            except Exception:
                pass

            time.sleep(self.PAGE_LOAD_WAIT)
            html = driver.page_source
            last_blocked = self._is_blocked_page(html)
            if last_blocked:
                time.sleep(2)
                continue

            result = self._parse(keyword, BeautifulSoup(html, "html.parser"))
            if result.total > 0:
                if result.seller_rocket > 0 and result.seller_rocket_max_review_count == 0:
                    self._hydrate_seller_rocket_reviews(driver, result)
                return result

        if last_blocked:
            raise RuntimeError("쿠팡 봇 차단 페이지가 반복해서 감지되었습니다.")

        raise TimeoutException(
            "쿠팡 검색 결과를 불러오지 못했습니다. "
            "자동화 크롬 창을 닫지 말고, 네트워크 상태를 확인한 뒤 다시 시도하세요."
        )

    def _run_search_attempt(
        self,
        driver: uc.Chrome,
        keyword: str,
        use_home_first: bool,
    ) -> None:
        if use_home_first:
            try:
                self._search_from_home(driver, keyword)
                return
            except TimeoutException:
                pass

        search_url = f"{self.BASE_URL}?q={quote(keyword)}&channel=user"
        driver.get(search_url)

    def _search_from_home(self, driver: uc.Chrome, keyword: str) -> None:
        """쿠팡 메인 검색창에 직접 입력해 사람 검색 흐름과 비슷하게 이동한다."""
        driver.get(self.HOME_URL)
        time.sleep(1.5)

        search_input = self._find_visible_search_input(driver)
        driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            search_input,
        )
        driver.execute_script("arguments[0].focus();", search_input)
        search_input.clear()
        search_input.send_keys(keyword)
        time.sleep(0.2)
        search_input.send_keys(Keys.ENTER)
        try:
            WebDriverWait(driver, self.RESULT_WAIT_TIMEOUT).until(
                EC.any_of(
                    EC.url_contains("/np/search"),
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, self.PRODUCT_SELECTOR)
                    ),
                )
            )
        except Exception:
            pass

    def _find_visible_search_input(self, driver: uc.Chrome):
        def find_input(_driver):
            inputs = _driver.find_elements(By.CSS_SELECTOR, self.SEARCH_INPUT_SELECTOR)
            for input_el in inputs:
                if input_el.is_displayed() and input_el.is_enabled():
                    return input_el
            return False

        return WebDriverWait(driver, self.RESULT_WAIT_TIMEOUT).until(find_input)

    def _hydrate_seller_rocket_reviews(self, driver: uc.Chrome, result: KeywordResult) -> None:
        """HTML 파싱만으로 리뷰 수가 비는 경우, 실제 DOM에서 보강한다."""
        elements = driver.find_elements(
            By.CSS_SELECTOR,
            "li.search-product, li[class*='ProductUnit']",
        )

        over_2000 = 0
        max_review = 0
        seller_seen = 0

        for element in elements:
            class_attr = f"{element.get_attribute('class') or ''} "
            if "search-product__ad" in class_attr:
                continue

            outer_html = element.get_attribute("outerHTML") or ""
            fragment = BeautifulSoup(outer_html, "html.parser")
            item = fragment.find(True)
            if item is None:
                continue

            if CoupangScraper._classify_badge(item) != "seller_rocket":
                continue

            seller_seen += 1
            review_count = CoupangScraper._extract_review_count(item)
            max_review = max(max_review, review_count)
            if review_count > 2000:
                over_2000 += 1

        if seller_seen == 0:
            return

        result.seller_rocket_max_review_count = max_review
        result.seller_rocket_review_over_2000 = over_2000

    def search_many(self, keywords: List[str]) -> List[KeywordResult]:
        return [self.search(kw) for kw in keywords]

    @staticmethod
    def _parse(keyword: str, soup: BeautifulSoup) -> KeywordResult:
        result = KeywordResult(keyword=keyword)

        items = soup.select("li.search-product, li[class*='ProductUnit']")

        for item in items:
            classes = " ".join(item.get("class") or [])
            if "search-product__ad" in classes or "ad-badge" in str(item):
                # 광고 제외
                continue

            result.total += 1
            badge_type = CoupangScraper._classify_badge(item)
            if badge_type == "rocket":
                result.rocket += 1
            elif badge_type == "seller_rocket":
                result.seller_rocket += 1
                review_count = CoupangScraper._extract_review_count(item)
                result.seller_rocket_max_review_count = max(
                    result.seller_rocket_max_review_count,
                    review_count,
                )
                if review_count > 2000:
                    result.seller_rocket_review_over_2000 += 1
            else:
                result.seller_delivery += 1

        return result

    @staticmethod
    def _is_blocked_page(html: str) -> bool:
        lowered = html.lower()
        blocked_markers = [
            "access denied",
            "akamai",
            "sec-if-cpt-container",
            "behavioral-content",
            "ret9999",
            "시스템 오류 발생",
        ]
        return any(marker in lowered for marker in blocked_markers)

    @staticmethod
    def _extract_review_count(item) -> int:
        """상품 카드에서 리뷰 수를 추출한다. 예: '(2,345)' -> 2345"""
        rating_selectors = [
            ".rating-total-count",
            "[class*='rating-total-count']",
            "[class*='rating-total']",
            "[class*='star-rating']",
            "[class*='rating-star']",
            "[class*='review-count']",
            "[class*='ReviewCount']",
            "[class*='ratingCnt']",
        ]

        candidates: List[int] = []

        for selector in rating_selectors:
            for node in item.select(selector):
                class_attr = CoupangScraper._class_string(node)
                if CoupangScraper._looks_like_price_text_node(class_attr):
                    continue
                text = node.get_text(" ", strip=True)
                candidates.extend(
                    CoupangScraper._review_numbers_from_rating_node(
                        text,
                        class_attr,
                    )
                )

        for node in CoupangScraper._fw_review_count_nodes(item):
            text = node.get_text(" ", strip=True)
            candidates.extend(
                CoupangScraper._review_numbers_from_fw_node(text)
            )

        if not candidates:
            item_text = item.get_text(" ", strip=True)
            for match in re.findall(r"\(([0-9,]+)\)", item_text):
                parsed = CoupangScraper._parse_count(match)
                if parsed is not None:
                    candidates.append(parsed)

        if not candidates:
            item_html = str(item)
            candidates.extend(
                CoupangScraper._numbers_from_embedded_json(item_html)
            )

        candidates = [
            count
            for count in candidates
            if 1 <= count <= 50_000_000
        ]

        return max(candidates, default=0)

    @staticmethod
    def _class_string(node) -> str:
        classes = node.get("class") or []
        if isinstance(classes, str):
            return classes
        return " ".join(classes)

    @staticmethod
    def _looks_like_price_text_node(class_attr: str) -> bool:
        lowered = class_attr.lower()
        return "fw-line-through" in lowered or "line-through" in lowered

    @staticmethod
    def _fw_review_count_nodes(item):
        for node in item.select('[class*="fw-inline-block"]'):
            class_attr = CoupangScraper._class_string(node)
            lowered = class_attr.lower()
            if "fw-line-through" in lowered:
                continue
            if "fw-text-[#212b36]" not in lowered:
                continue
            yield node

    @staticmethod
    def _review_numbers_from_fw_node(text: str) -> List[int]:
        stripped = text.strip()
        paren_match = re.fullmatch(
            r"\(\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)\s*\)",
            stripped,
        )
        if not paren_match:
            return []

        parsed = CoupangScraper._parse_count(paren_match.group(1))
        return [parsed] if parsed is not None else []

    @staticmethod
    def _review_numbers_from_rating_node(text: str, class_attr: str) -> List[int]:
        lowered = class_attr.lower()
        paren_only = CoupangScraper._review_numbers_from_fw_node(text)
        if paren_only:
            return paren_only

        if any(
            token in lowered
            for token in (
                "rating-total-count",
                "reviewcount",
                "ratingcnt",
            )
        ):
            return CoupangScraper._numbers_from_text(text)

        return []

    @staticmethod
    def _numbers_from_embedded_json(html_fragment: str) -> List[int]:
        patterns = [
            r'(?i)ratingTotalCount["\']?\s*[:=]\s*["\']?(\d{1,3}(?:,\d{3})*|\d+)',
            r'(?i)reviewCount["\']?\s*[:=]\s*["\']?(\d{1,3}(?:,\d{3})*|\d+)',
            r'(?i)ratingCount["\']?\s*[:=]\s*["\']?(\d{1,3}(?:,\d{3})*|\d+)',
        ]
        numbers: List[int] = []
        for pattern in patterns:
            for match in re.findall(pattern, html_fragment):
                parsed = CoupangScraper._parse_count(match)
                if parsed is not None:
                    numbers.append(parsed)
        return numbers

    @staticmethod
    def _numbers_from_text(text: str) -> List[int]:
        numbers: List[int] = []

        for match in re.findall(r"([0-9,]+)", text):
            parsed = CoupangScraper._parse_count(match)
            if parsed is None:
                continue
            numbers.append(parsed)

        return numbers

    @staticmethod
    def _parse_count(text: str) -> Optional[int]:
        match = re.search(r"([0-9,]+)", text)
        if not match:
            return None
        return int(match.group(1).replace(",", ""))

    @staticmethod
    def _classify_badge(item) -> str:
        """배지 종류 판별: 'rocket' | 'seller_rocket' | 'seller_delivery'."""
        badges = item.select("img")
        for badge in badges:
            src = (badge.get("src") or "").lower()
            alt = (badge.get("alt") or "").lower()
            blob = f"{src} {alt}"

            # 판매자로켓 (merchant rocket / jet)
            if "merchant" in blob or "jet" in blob or "판매자로켓" in alt:
                return "seller_rocket"

            # 로켓배송 / 로켓프레시 / 로켓직구
            if (
                "rocket" in blob
                or "fresh" in blob
                or "global" in blob
                or "로켓" in alt
            ):
                return "rocket"

        return "seller_delivery"
