# Contributing to Speak Helper

Thank you for improving this **text-to-speech**, **clipboard read-aloud**, and **OCR-to-speech** desktop tool.

## Development setup

```powershell
uv sync --extra dev
.\scripts\check.ps1
```

Requirements: Python 3.11+, Windows / macOS / Linux with a display (PySide6).

## Code style

- Match existing module layout: services in `speak_helper/`, UI in `speak_helper/ui/`
- Use `from __future__ import annotations` in new Python files
- Prefer small, focused changes; avoid unrelated refactors in the same PR
- Keep code, identifiers, comments, logs, tests, commits, and technical docs in English
- Put every user-facing string in both centralized `en` and `fr` catalogs
- Keep UI logic separate from hotkey, clipboard, HTTP, and playback services

## Pull request checklist

- [ ] `.\scripts\check.ps1` passes
- [ ] New config keys added to `DEFAULT` in `config.py` and `config.example.json`
- [ ] User-facing changes reflected in English and `docs/fr/` documentation
- [ ] `CHANGELOG.md` updated under `Unreleased` or a new version section

## Reporting issues

Include:

- OS version (e.g. Windows 11, macOS 14)
- Python version
- TTS backend (`edge` or `openai`) and provider URL if applicable
- Steps to reproduce (clipboard / hotkey / OCR)
- Diagnostics copied from Settings and the structured `speak-helper.log`

## Security

Do not open public issues for API key leaks. See [SECURITY.md](SECURITY.md).
