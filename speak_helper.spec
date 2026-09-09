"""PyInstaller specification for Speak Helper."""

block_cipher = None

hiddenimports = [
    # Cross-platform pynput fallbacks.
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    # Windows credential storage.
    "keyring.backends.Windows",
    "keyring.backends.fail",
    # Edge-TTS runtime modules and networking.
    "edge_tts",
    "edge_tts.communicate",
    "edge_tts.exceptions",
    "edge_tts.voices",
    "aiohttp",
    "aiohttp.resolver",
    "aiohttp.connector",
    # OCR image conversion.
    "PIL",
    "PIL.Image",
    "PIL.ImageDraw",
    "PIL.JpegImagePlugin",
    "PIL.PngImagePlugin",
    "asyncio",
    "asyncio.selector_events",
    "httpx",
    # Qt multimedia and SVG icon rendering.
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
    excludes=["tkinter", "matplotlib", "numpy", "pandas", "scipy"],
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
    upx=False,
    console=False,
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
