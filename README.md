# Speak Helper

**Read selected text aloud with one click** — a lightweight desktop **text-to-speech (TTS)** assistant for **Windows**, **macOS**, and **Linux**.

[English](README.md) · [中文](README_zh.md)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **Also known as:** clipboard TTS, read-aloud tool, screen text speaker, OCR-to-speech, OpenAI TTS client, Edge TTS desktop app, 文字转语音, 剪贴板朗读, 选中朗读.

## Use cases

Speak Helper turns on-screen text into speech — useful whenever **reading is tiring, difficult, or inconvenient**.

### Prefer listening over reading

| Scenario | Example |
|----------|---------|
| **Too tired to read** | Listen to articles, emails, or chat messages after a long day |
| **Long documents** | Hear reports or PDF excerpts without scrolling line by line |
| **Small / dense UI** | Copy text from apps with cramped fonts and let it read aloud |

### Vision & reading support

| Scenario | Example |
|----------|---------|
| **Low vision** | Hear selected text from browsers, PDFs, or desktop apps (complements—not replaces—full screen readers) |
| **Eye strain / fatigue** | Reduce screen time by listening to copied paragraphs |
| **Elderly users** | Family can help set hotkeys; copy a message or news snippet to hear it clearly |
| **Dyslexia / reading difficulty** | Audio reinforces written content from any app |

> **Note:** Speak Helper is a **read-aloud assistant** for text you copy or select. It is **not** a full screen reader (NVDA, VoiceOver). It works well **alongside** those tools or when you only need occasional listening.

### Daily productivity

| Scenario | Example |
|----------|---------|
| **Multitasking** | Listen while coding, cooking, exercising, or commuting |
| **Language learning** | Natural Chinese / English neural voices for listening practice |
| **Screenshot & image text** | Copy a screenshot → OCR extracts text → automatic read-aloud |
| **Quick workflow** | `Ctrl+Alt+R` on selected text — no browser extension required |

## Features

- **Floating dock** on screen edge — states: idle, speaking, paused, error
- **Clipboard trigger** — copy text → prompt bubble (ask mode) or auto speak
- **Global hotkey** — `Ctrl+Alt+R` reads currently selected text
- **Ask / Auto modes** — switch from tray menu
- **Two TTS backends**
  - **Edge TTS** (Microsoft neural voices, no API key)
  - **OpenAI-compatible API** (`/audio/speech`) — OpenAI, DashScope, SiliconFlow, self-hosted
- **Clipboard image OCR** — vision API extracts text, then TTS (PaddleOCR-VL, etc.)
- **Streaming playback** — sentence chunking, fetch-and-play pipeline
- **Local audio cache** — same text skips API calls
- **Secure API key** — system keyring + config file
- **Single instance** — Windows named mutex

## Quick start

### Install

```powershell
cd speak_helper
uv venv
uv sync
```

Or with pip:

```bash
pip install -r requirements.txt
```

### Run

```bash
uv run python -m speak_helper
# or: speak-helper  (after pip install -e .)
```

First run: right-click **system tray** → **Settings** → choose TTS backend and API key (if using OpenAI-compatible mode).

### Default backends

| Backend | API key | Notes |
|---------|---------|-------|
| `edge` (default) | Not required | Uses `edge-tts` / Microsoft neural voices |
| `openai` | Required | Any OpenAI-compatible `/audio/speech` endpoint |

See [docs/configuration.md](docs/configuration.md) for all options.

**Optional `.env`:** copy [`.env.example`](.env.example) if you want team defaults. **Model fields in `.env` are optional** — configure in ⚙ Settings. Priority: `config.json` → `.env` → defaults.

## Keyboard shortcuts

| Action | Shortcut |
|--------|----------|
| Speak selection | `Ctrl+Alt+R` |
| Confirm bubble | `Enter` |
| Cancel bubble | `Esc` |
| Pause / resume listening | Single-click floating dock |
| Replay last text | Double-click floating dock |

## Build executable

**Windows**

```powershell
.\scripts\build_win.ps1
# Output: dist\SpeakHelper\SpeakHelper.exe
```

**macOS**

```bash
bash scripts/build_mac.sh
# Output: dist/SpeakHelper.app
```

## Documentation

| Topic | English | 中文 |
|-------|---------|------|
| Index | [docs/README.md](docs/README.md) | [docs/zh/README.md](docs/zh/README.md) |
| Installation | [docs/installation.md](docs/installation.md) | [docs/zh/installation.md](docs/zh/installation.md) |
| Configuration | [docs/configuration.md](docs/configuration.md) | [docs/zh/configuration.md](docs/zh/configuration.md) |
| FAQ | [docs/faq.md](docs/faq.md) | [docs/zh/faq.md](docs/zh/faq.md) |
| Use cases | [docs/use-cases.md](docs/use-cases.md) | [docs/zh/use-cases.md](docs/zh/use-cases.md) |
| Architecture | [docs/architecture.md](docs/architecture.md) | [docs/zh/architecture.md](docs/zh/architecture.md) |

## Tests

```bash
uv run pytest tests/
```

## Project layout

```
speak_helper/
├── speak_helper/          # Python package
│   ├── main.py            # App controller & wiring
│   ├── config.py          # JSON config + keyring
│   ├── speech_service.py  # TTS (edge + OpenAI-compatible)
│   ├── ocr_service.py     # Vision OCR for clipboard images
│   ├── clipboard_watcher.py
│   ├── hotkey_service.py
│   ├── audio_player.py
│   └── ui/                # PySide6 widgets
├── docs/                  # User & contributor docs
├── scripts/               # Build scripts
├── tests/
├── pyproject.toml
└── config.example.json
```

## Privacy

- Text is sent only to **your configured TTS / OCR API** (or Microsoft Edge TTS for `edge` backend).
- No third-party analytics or relay servers.
- API keys stored in OS credential store when possible.
- Local cache lives in the user config directory; clear from Settings.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) ([中文](CONTRIBUTING_zh.md)).

## License

[MIT License](LICENSE) — Copyright (c) 2026 Speak Helper contributors.

## Search keywords

`text-to-speech`, `TTS`, `read aloud`, `clipboard reader`, `global hotkey TTS`, `PySide6`, `Qt desktop`, `Edge TTS`, `OpenAI speech API`, `CosyVoice`, `MOSS-TTS`, `OCR to speech`, `PaddleOCR`, `vision API`, `accessibility`, `dyslexia`, `文字转语音`, `朗读助手`, `剪贴板朗读`, `全局快捷键`, `识图朗读`.
