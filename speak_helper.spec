# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for speak_helper (Windows x64)
"""

import sys
from pathlib import Path

block_cipher = None

# ── 收集 pynput 在 Windows 上必需的后端 ──────────────────────────────────────
hiddenimports = [
    # pynput Windows 后端
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    # keyring Windows 后端
    "keyring.backends.Windows",
    "keyring.backends.fail",
    # edge_tts 内部依赖
    "edge_tts",
    "edge_tts.communicate",
    "edge_tts.exceptions",
    "edge_tts.list_voices",
    # aiohttp（edge_tts 运行时依赖）
    "aiohttp",
    "aiohttp.resolver",
    "aiohttp.connector",
    # Pillow
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
    # asyncio
    "asyncio",
    "asyncio.selector_events",
    # httpx
    "httpx",
    # PySide6 媒体相关
    "PySide6.QtMultimedia",
    "PySide6.QtSvg",
    "PySide6.QtSvgWidgets",
]

a = Analysis(
    ["speak_helper/__main__.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "scipy",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SpeakHelper",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # Windows 上 UPX 可能破坏 PySide6 DLL，保持关闭
    console=False,      # GUI 应用，不显示命令行窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="icon.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SpeakHelper",
)
