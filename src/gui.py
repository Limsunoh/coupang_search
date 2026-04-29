"""Tkinter 기반 GUI."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List

from src.scraper import CoupangScraper, KeywordResult


class App(tk.Tk):
    MAX_KEYWORDS = 100

    def __init__(self) -> None:
        super().__init__()
        self.title("Coupang Keyword Analyzer")
        self.geometry("1000x650")

        # 쿠팡이 헤드리스를 차단하므로 창이 뜨는 모드로 사용한다.
        self.scraper = CoupangScraper(headless=False)
        self._is_running = False

        self._build_widgets()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_widgets(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(
            top,
            text=f"키워드 (한 줄에 하나씩, 최대 {self.MAX_KEYWORDS}개)",
        ).pack(anchor="w")

        self.text_input = tk.Text(top, height=8)
        self.text_input.pack(fill="x", pady=(4, 8))

        self.run_button = ttk.Button(top, text="분석 시작", command=self.on_run)
        self.run_button.pack(anchor="e")

        self.status_var = tk.StringVar(value="대기 중")
        ttk.Label(self, textvariable=self.status_var, padding=(10, 0)).pack(anchor="w")

        # 결과 테이블 + 스크롤바
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = (
            "keyword",
            "total",
            "rocket",
            "seller_rocket",
            "seller_delivery",
            "rocket_ratio",
            "seller_rocket_ratio",
            "seller_delivery_ratio",
        )
        headings = {
            "keyword": "키워드",
            "total": "전체",
            "rocket": "로켓",
            "seller_rocket": "판매자로켓",
            "seller_delivery": "판매자배송",
            "rocket_ratio": "로켓 %",
            "seller_rocket_ratio": "판매자로켓 %",
            "seller_delivery_ratio": "판매자배송 %",
        }
        widths = {
            "keyword": 200,
            "total": 70,
            "rocket": 70,
            "seller_rocket": 90,
            "seller_delivery": 90,
            "rocket_ratio": 90,
            "seller_rocket_ratio": 110,
            "seller_delivery_ratio": 110,
        }

        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        for col in columns:
            anchor = "w" if col == "keyword" else "center"
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor=anchor)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def on_run(self) -> None:
        if self._is_running:
            return

        raw = self.text_input.get("1.0", "end").strip()
        keywords = [line.strip() for line in raw.splitlines() if line.strip()]

        if not keywords:
            messagebox.showwarning("입력 필요", "키워드를 1개 이상 입력하세요.")
            return
        if len(keywords) > self.MAX_KEYWORDS:
            messagebox.showwarning(
                "제한 초과",
                f"키워드는 최대 {self.MAX_KEYWORDS}개까지 입력할 수 있습니다.",
            )
            return

        self._is_running = True
        self.run_button.config(state="disabled")
        self.tree.delete(*self.tree.get_children())
        self.status_var.set(
            f"분석 중... (0 / {len(keywords)})  · 첫 검색은 봇 차단 통과로 5~10초 소요"
        )

        threading.Thread(target=self._run_scrape, args=(keywords,), daemon=True).start()

    def _run_scrape(self, keywords: List[str]) -> None:
        total = len(keywords)
        for idx, kw in enumerate(keywords, 1):
            try:
                result = self.scraper.search(kw)
            except Exception as exc:
                result = KeywordResult(keyword=kw)
                self.after(0, self._append_error_row, kw, str(exc))
            else:
                self.after(0, self._append_row, result)

            self.after(0, self.status_var.set, f"분석 중... ({idx} / {total})")

        self.after(0, self._on_done, total)

    def _append_row(self, result: KeywordResult) -> None:
        d = result.to_dict()
        item = self.tree.insert(
            "",
            "end",
            values=(
                d["keyword"],
                d["total"],
                d["rocket"],
                d["seller_rocket"],
                d["seller_delivery"],
                f'{d["rocket_ratio"]}%',
                f'{d["seller_rocket_ratio"]}%',
                f'{d["seller_delivery_ratio"]}%',
            ),
        )
        self.tree.see(item)

    def _append_error_row(self, keyword: str, message: str) -> None:
        item = self.tree.insert(
            "",
            "end",
            values=(keyword, f"실패: {message[:40]}", "", "", "", "", "", ""),
        )
        self.tree.see(item)

    def _on_done(self, count: int) -> None:
        self.status_var.set(f"완료 ({count}건)")
        self.run_button.config(state="normal")
        self._is_running = False

    def _on_close(self) -> None:
        try:
            self.scraper.close()
        finally:
            self.destroy()


def run() -> None:
    app = App()
    app.mainloop()
