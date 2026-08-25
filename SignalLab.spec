# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all
from pathlib import Path

webview_datas, webview_binaries, webview_hidden = collect_all("webview")
native_dir = Path("backend/app")
native_binaries = [
    (str(path), "backend/app")
    for pattern in ("_native_core*.pyd", "tbb*.dll")
    for path in native_dir.glob(pattern)
]

a = Analysis(
    ["backend/desktop.py"],
    pathex=["."],
    binaries=webview_binaries + native_binaries,
    datas=webview_datas + [("frontend/dist", "frontend/dist")],
    hiddenimports=webview_hidden + ["backend.app._native_core"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["PyQt5", "PyQt6", "PySide2", "PySide6", "cefpython3", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SignalLab",
    icon="assets/app.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="SignalLab",
)
