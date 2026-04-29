"""단일 키워드 스크래핑 테스트."""

from src.scraper import CoupangScraper


def main() -> None:
    keyword = "접이식 우산"
    print(f"[TEST] keyword = {keyword}")

    with CoupangScraper(headless=False) as scraper:
        result = scraper.search(keyword)

    print("=" * 40)
    print(f"키워드        : {result.keyword}")
    print(f"전체 상품 수  : {result.total}")
    print(f"로켓배송      : {result.rocket}개 ({result.rocket_ratio*100:.1f}%)")
    print(f"판매자로켓    : {result.seller_rocket}개 ({result.seller_rocket_ratio*100:.1f}%)")
    print(f"판매자배송    : {result.seller_delivery}개 ({result.seller_delivery_ratio*100:.1f}%)")
    print("=" * 40)


if __name__ == "__main__":
    main()
