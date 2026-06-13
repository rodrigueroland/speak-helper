# Contributing to Speak Helper

[English](CONTRIBUTING.md) · [中文](CONTRIBUTING_zh.md)

Thank you for improving this **text-to-speech**, **clipboard read-aloud**, and **OCR-to-speech** desktop tool.

## Development setup

```powershell
cd speak_helper
uv venv
uv sync --all-extras
uv run pytest tests/
```

Requirements: Python 3.11+, Windows / macOS / Linux with a display (PySide6).

## Code style

- Match existing module layout: services in `speak_helper/`, UI in `speak_helper/ui/`
- Use `from __future__ import annotations` in new Python files
- Prefer small, focused changes; avoid unrelated refactors in the same PR
- UI strings may stay Chinese for now; document user-facing behavior in **both** `docs/` and `docs/zh/`

## Pull request checklist

- [ ] `uv run pytest tests/` passes
- [ ] New config keys added to `DEFAULT` in `config.py` and `config.example.json`
- [ ] User-facing changes reflected in `docs/` (EN) and `docs/zh/` (ZH)
- [ ] `CHANGELOG.md` updated under `Unreleased` or a new version section

## Reporting issues

Include:

- OS version (e.g. Windows 11, macOS 14)
- Python version
- TTS backend (`edge` or `openai`) and provider URL if applicable
- Steps to reproduce (clipboard / hotkey / OCR)
- Relevant log: `%APPDATA%\speak_helper\ocr.log` on Windows (OCR only)

## Security

Do not open public issues for API key leaks. See [SECURITY.md](SECURITY.md).
