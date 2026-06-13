#!/usr/bin/env bash
# Speak Helper macOS 打包脚本（PyInstaller）
# 用法：bash scripts/build_mac.sh
# 产物：dist/SpeakHelper.app

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ">> 安装依赖..."
pip install -r requirements.txt -q
pip install pyinstaller -q

echo ">> 开始打包..."
pyinstaller \
    --noconfirm \
    --onedir \
    --noconsole \
    --name "SpeakHelper" \
    --windowed \
    --hidden-import "PySide6.QtSvg" \
    --hidden-import "PySide6.QtMultimedia" \
    --hidden-import "pynput.keyboard._darwin" \
    --hidden-import "pynput.mouse._darwin" \
    --hidden-import "keyring.backends.macOS" \
    speak_helper/__main__.py

echo ""
echo "✅ 打包完成：dist/SpeakHelper.app"
