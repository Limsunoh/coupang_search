# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.building.api import EXE
from PyInstaller.building.build_main import Analysis, PYZ
from PyInstaller.utils.hooks import collect_all, collect_submodules

_hidden = []
for pkg in (
    "selenium",
    "selenium.webdriver",
    "selenium.webdriver.chrome",
    "selenium.webdriver.common",
    "selenium.webdriver.remote",
    "urllib3",
    "certifi",
    "websockets",
    "trio",
    "trio_websocket",
    "outcome",
    "wsproto",
    "sniffio",
    "attrs",
    "sortedcontainers",
    "openpyxl",
):
    _hidden.extend(collect_submodules(pkg))

datas_uc, binaries_uc, hidden_uc = collect_all("undetected_chromedriver")

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries_uc,
    datas=datas_uc,
    hiddenimports=list(dict.fromkeys(hidden_uc + _hidden)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="CoupangKeywordAnalyzer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
