# Installation

[English](installation.md) · [中文](../zh/installation.md)

Install Speak Helper — a **cross-platform desktop TTS / read-aloud** tool for Windows, macOS, and Linux.

## Requirements

| Item | Version |
|------|---------|
| Python | 3.11+ (3.13 recommended) |
| Display | Required (PySide6 GUI) |
| Audio | System audio output |

Optional for builds: [uv](https://docs.astral.sh/uv/), PyInstaller (included in dev extras).

## Install with uv (recommended)

```powershell
cd speak_helper
uv venv
uv sync
uv run python -m speak_helper
```

Install dev tools (pytest, pyinstaller):

```powershell
uv sync --all-extras
```

## Install with pip

```bash
cd speak_helper
pip install -r requirements.txt
python -m speak_helper
```

Editable install (CLI entry `speak-helper`):

```bash
pip install -e ".[dev]"
speak-helper
```

## Windows notes

- **Antivirus**: `pynput` global hotkeys may trigger warnings; whitelist the Python or `SpeakHelper.exe` process.
- **Single instance**: Second launch shows a tray reminder; check the system tray icon.
- **Config directory**: `%APPDATA%\speak_helper\` (or `%LOCALAPPDATA%` per `platformdirs`).

## macOS notes

- Grant **Accessibility** permission if hotkey capture fails (System Settings → Privacy).
- Build: `bash scripts/build_mac.sh` → `dist/SpeakHelper.app`.

## Linux notes

- Install Qt multimedia dependencies if audio playback fails (distro-specific `libqt6multimedia` packages).
- Hotkeys may require X11 or appropriate permissions on Wayland.

## Build standalone executable

### Windows

```powershell
.\scripts\build_win.ps1
```

Output: `dist\SpeakHelper\SpeakHelper.exe` and `dist\SpeakHelper-win64.zip`.

### macOS

```bash
bash scripts/build_mac.sh
```

Output: `dist/SpeakHelper.app`.

## Verify installation

```bash
uv run pytest tests/ -q
```

## Uninstall

- Remove the project folder.
- Delete user config: `speak_helper` under your OS config dir (cache + `config.json`).
- Remove API key from Windows Credential Manager / macOS Keychain (service name `speak_helper`).
