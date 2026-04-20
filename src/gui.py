"""Tkinter 기반 GUI (스켈레톤)."""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List

from src.scraper import CoupangScraper, KeywordResult


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Coupang Keyword Analyzer")
        self.geometry("900x600")

        self.scraper = CoupangScraper(headless=True)

        self._build_widgets()

    def _build_widgets(self) -> None:
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")

        ttk.Label(top, text="키워드 (한 줄에 하나씩, 최대 100개)").pack(anchor="w")

        self.text_input = tk.Text(top, height=8)
        self.text_input.pack(fill="x", pady=(4, 8))

        self.run_button = ttk.Button(top, text="분석 시작", command=self.on_run)
        self.run_button.pack(anchor="e")

        self.status_var = tk.StringVar(value="대기 중")
        ttk.Label(self, textvariable=self.status_var, padding=(10, 0)).pack(anchor="w")

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

        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for col in columns:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def on_run(self) -> None:
        raw = self.text_input.get("1.0", "end").strip()
        keywords = [line.strip() for line in raw.splitlines() if line.strip()]

        if not keywords:
            messagebox.showwarning("입력 필요", "키워드를 1개 이상 입력하세요.")
            return
        if len(keywords) > 100:
            messagebox.showwarning("제한 초과", "키워드는 최대 100개까지 입력할 수 있습니다.")
            return

        self.run_button.config(state="disabled")
        self.status_var.set(f"분석 중... (0 / {len(keywords)})")
        self.tree.delete(*self.tree.get_children())

        threading.Thread(target=self._run_scrape, args=(keywords,), daemon=True).start()

    def _run_scrape(self, keywords: List[str]) -> None:
        results: List[KeywordResult] = []
        for idx, kw in enumerate(keywords, 1):
            result = self.scraper.search(kw)
            results.append(result)
            self.after(0, self._append_row, result)
            self.after(0, self.status_var.set, f"분석 중... ({idx} / {len(keywords)})")

        self.after(0, self._on_done, len(results))

    def _append_row(self, result: KeywordResult) -> None:
        d = result.to_dict()
        self.tree.insert(
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

    def _on_done(self, count: int) -> None:
        self.status_var.set(f"완료 ({count}건)")
        self.run_button.config(state="normal")


def run() -> None:
    app = App()
    app.mainloop()
