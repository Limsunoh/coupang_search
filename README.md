# coupang-keyword-analyzer

쿠팡에서 키워드를 검색했을 때 1페이지에 로켓배송/판매자로켓/판매자배송 상품이
각각 몇 개씩 걸리는지 확인하는 툴.

키워드 소싱할 때마다 쿠팡 들어가서 일일이 세는 게 귀찮아서 만듦.

## 쓰는 법

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

키워드를 한 줄에 하나씩 넣고 돌리면 표로 결과가 나옴. 최대 100개.

## 구조

```
├── main.py
├── src/
│   ├── scraper.py    # 쿠팡 검색/파싱
│   └── gui.py        # tkinter GUI
└── requirements.txt
```

## TODO

- [x] 스켈레톤
- [ ] 스크래핑 로직
- [ ] 로켓 / 판매자로켓 / 판매자배송 판별
- [ ] 결과 CSV 저장
- [ ] exe 빌드
