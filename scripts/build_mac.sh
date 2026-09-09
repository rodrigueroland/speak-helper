#!/usr/bin/env bash
# Speak Helper macOS build script.

set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo ">> Syncing dependencies..."
uv sync --extra dev

echo ">> Building..."
uv run pyinstaller \
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
echo "Build complete: dist/SpeakHelper.app"
