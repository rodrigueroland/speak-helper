# Speak Helper Documentation

[English](README.md) · [中文](../zh/README.md)

Speak Helper is a **desktop text-to-speech (TTS)** application: **read aloud** selected or copied text, with optional **OCR-to-speech** for clipboard images.

## Guides

| Guide | Description |
|-------|-------------|
| [Installation](installation.md) | Python, uv, pip, PyInstaller builds |
| [Configuration](configuration.md) | TTS backends, OCR, triggers, cache |
| [Use cases](use-cases.md) | Listen instead of read, vision support, productivity |
| [FAQ](faq.md) | Troubleshooting, providers, accessibility |
| [Architecture](architecture.md) | Modules, signals, data flow |

## Quick links

- **No API key?** Use default `edge` backend (Microsoft neural voices via Edge TTS).
- **OpenAI / SiliconFlow / DashScope?** Set `tts.backend` to `openai` and configure `base_url`.
- **Screenshot text?** Copy image to clipboard; OCR runs when `ocr.enabled` is true.

## Related terms (search)

`TTS`, `text-to-speech`, `read aloud`, `clipboard TTS`, `global hotkey`, `Edge TTS`, `OpenAI speech API`, `CosyVoice`, `MOSS-TTS`, `PaddleOCR`, `vision OCR`, `PySide6`, `Qt`, `accessibility`, `dyslexia`, `screen reader companion`.
