"""쿠팡 검색 결과 스크래핑 모듈 (스켈레톤)."""

from dataclasses import dataclass, asdict
from typing import List


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
    """쿠팡 키워드 검색 스크래퍼 (스켈레톤)."""

    BASE_URL = "https://www.coupang.com/np/search"

    def __init__(self, headless: bool = True) -> None:
        self.headless = headless

    def search(self, keyword: str) -> KeywordResult:
        """키워드 1개를 검색하고 1페이지 결과를 집계한다.

        TODO: Selenium/BeautifulSoup으로 실제 스크래핑 구현
        """
        return KeywordResult(keyword=keyword)

    def search_many(self, keywords: List[str]) -> List[KeywordResult]:
        """여러 키워드를 순차적으로 검색한다."""
        return [self.search(kw) for kw in keywords]
