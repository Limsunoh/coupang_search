"""쿠팡 검색 결과 스크래핑 모듈."""

from __future__ import annotations

import time
from dataclasses import dataclass, asdict
from typing import List, Optional
from urllib.parse import quote

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
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

    @property
    def rocket_ratio(self) -> float:
        return self.rocket / self.total if self.total else 0.0

    @property
    def seller_rocket_ratio(self) -> float:
        return self.seller_rocket / self.total if self.total else 0.0

    @property
    def seller_delivery_ratio(self) -> float:
        return self.seller_delivery / self.total if self.total else 0.0

    def to_dict(self) -> dict:
        data = asdict(self)
        data["rocket_ratio"] = round(self.rocket_ratio * 100, 1)
        data["seller_rocket_ratio"] = round(self.seller_rocket_ratio * 100, 1)
        data["seller_delivery_ratio"] = round(self.seller_delivery_ratio * 100, 1)
        return data


class CoupangScraper:
    """쿠팡 키워드 검색 스크래퍼."""

    BASE_URL = "https://www.coupang.com/np/search"
    PAGE_LOAD_WAIT = 3.5
    RESULT_WAIT_TIMEOUT = 25
    PRODUCT_SELECTOR = "li.search-product, li[class*='ProductUnit']"

    def __init__(self, headless: bool = True, chrome_version: Optional[int] = None) -> None:
        self.headless = headless
        self.chrome_version = chrome_version or self._detect_chrome_major_version()
        self._driver: Optional[uc.Chrome] = None

    @staticmethod
    def _detect_chrome_major_version() -> Optional[int]:
        """설치된 Chrome의 메이저 버전을 감지한다 (Windows 기준)."""
        import os
        import re
        import subprocess

        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
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
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument("--headless=new")
        options.add_argument("--lang=ko-KR")
        options.add_argument("--window-size=1280,900")
        options.add_argument("--disable-blink-features=AutomationControlled")
        kwargs = {"options": options}
        if self.chrome_version:
            kwargs["version_main"] = self.chrome_version
        return uc.Chrome(**kwargs)

    def _ensure_driver(self) -> uc.Chrome:
        if self._driver is None:
            self._driver = self._build_driver()
        return self._driver

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
        url = f"{self.BASE_URL}?q={quote(keyword)}&channel=user"
        driver.get(url)

        # Akamai 챌린지 통과 + 검색 결과 로드까지 대기
        try:
            WebDriverWait(driver, self.RESULT_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, self.PRODUCT_SELECTOR))
            )
        except Exception:
            pass

        time.sleep(self.PAGE_LOAD_WAIT)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        return self._parse(keyword, soup)

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
            else:
                result.seller_delivery += 1

        return result

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
            if "rocket" in blob or "fresh" in blob or "global" in blob or "로켓" in alt:
                return "rocket"

        return "seller_delivery"
