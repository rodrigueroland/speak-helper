# Changelog

All notable changes to Speak Helper are documented in this file.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- Complete English and French UI catalogs with runtime language switching
- Native Windows global hotkeys for Read, Stop, Pause/Resume, and Replay
- Transactional selected-text capture with clipboard sequence detection and restore
- Conservative Markdown/code/URL preprocessing
- Diagnostics panel and structured rotating logs
- Qwen3-TTS local preset through the OpenAI-compatible backend
- Repeatable Windows selection probe and expanded automated tests
- Published Qwen3-TTS CustomVoice defaults with automatic English/French hints
- Loopback HTTP integration coverage for custom and Qwen-compatible servers
- OCR response, authentication, and cancellation coverage
- Optional per-user Windows launch-at-login integration

### Changed

- Manual Selection is now the safe default clipboard mode
- New readings immediately replace obsolete synthesis and playback
- Local OpenAI-compatible endpoints no longer require a non-empty API key
- OCR is disabled by default, isolated, and no longer logs full recognized text
- Windows packaging and CI now include explicit quality and smoke checks

### Fixed

- Replaced the unreliable Qt timer created from a plain hotkey thread
- Report global hotkey conflicts instead of failing silently
- Release completed audio file handles on Windows
- Use correct 64-bit Windows mutex and input structure declarations

## [0.0.1] - 2026-06-13

### Added

- Initial public release: desktop TTS assistant (clipboard, hotkey, OCR-to-speech)
- Edge TTS and OpenAI-compatible `/audio/speech` backends
- PySide6 UI: floating dock, tray, settings panel
- Optional `.env` fallback (models configurable in Settings; not required in `.env`)
- Open-source docs (English default, Chinese mirror), MIT license, CI workflow

[0.0.1]: https://github.com/archoor/speak-helper/releases/tag/v0.0.1
