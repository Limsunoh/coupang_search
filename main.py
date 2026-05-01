"""Coupang Keyword Analyzer 진입점."""

import ctypes
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path


def _crash_log_path() -> Path:
    base = os.getenv("LOCALAPPDATA") or str(Path.home())
    log_dir = Path(base) / "CoupangKeywordAnalyzer" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"crash_{datetime.now():%Y%m%d_%H%M%S}.log"


def _show_error(title: str, message: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10)
    except Exception:
        print(message, file=sys.stderr)


if getattr(sys, "frozen", False):
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass and meipass not in sys.path:
        sys.path.insert(0, meipass)


if __name__ == "__main__":
    try:
        from src.gui import run

        run()
    except Exception:
        log_path = _crash_log_path()
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        _show_error(
            "CoupangKeywordAnalyzer 오류",
            "프로그램 시작 중 오류가 발생했습니다.\n\n"
            f"로그: {log_path}",
        )
        sys.exit(1)
