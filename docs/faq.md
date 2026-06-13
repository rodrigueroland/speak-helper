# FAQ — Frequently Asked Questions

[English](faq.md) · [中文](../zh/faq.md)

Common questions about **Speak Helper** — desktop **TTS**, **read aloud**, **clipboard speaker**, and **OCR-to-speech**.

## General

### What is Speak Helper?

A lightweight **PySide6** desktop app that **reads text aloud** using **text-to-speech (TTS)**. Trigger via **clipboard copy**, **global hotkey** (`Ctrl+Alt+R`), or **clipboard image** (OCR then TTS).

### Who should use Speak Helper?

See the full [Use cases](use-cases.md) guide. In short:

- **Prefer listening** — tired eyes, long text, multitasking.
- **Vision / reading support** — low vision, eye strain, elderly users, dyslexia (for **copied/selected** text, not full UI navigation).
- **Learning & OCR** — language practice, screenshot text read aloud.

### Is it a screen reader?

No. It is a **read-aloud assistant** for text you select or copy—not a full **accessibility screen reader** like NVDA or VoiceOver. It complements workflows for **low vision listening**, **dyslexia**, **multitasking**, and **language learning**.

### Does it work offline?

- **Edge TTS backend**: synthesis uses Microsoft Edge TTS online; no API key.
- **OpenAI-compatible backend**: requires network to your API.
- **UI and cache**: local. Cached audio replays without network.

## TTS & API

### Which TTS backend should I use?

| Need | Backend |
|------|---------|
| Free, no API key, good Chinese voices | `edge` |
| Custom models (CosyVoice, MOSS-TTS, OpenAI) | `openai` |

### OpenAI TTS vs Edge TTS vs CosyVoice?

- **OpenAI `tts-1`**: stable, paid, English-focused voices (`nova`, `alloy`, …).
- **Edge TTS**: free neural voices (`zh-CN-XiaoxiaoNeural`, …).
- **CosyVoice / MOSS-TTS** (via SiliconFlow): open models on compatible `/audio/speech` endpoints.

### Why does hotkey speak nothing?

1. Ensure text is **selected** before pressing the hotkey.
2. Check tray menu: hotkey and clipboard not disabled / app not paused.
3. On macOS, grant Accessibility permission for `pynput`.
4. Some apps block simulated Ctrl+C.

### API errors / 401 / timeout

- Verify `base_url` has no trailing path beyond `/v1`.
- Check API key in Settings; test with provider dashboard.
- Increase `tts.timeout_sec` for slow models.
- SiliconFlow voices often use `model:voice_name` format.

## Clipboard & OCR

### Copy triggers too often / duplicate reads

- Default **ask mode** shows a bubble; switch to **auto** in tray if desired.
- **Dedup** ignores identical consecutive clipboard text.
- Adjust `trigger.debounce_ms` and `trigger.min_length`.

### How does image / screenshot TTS work?

1. Copy image to clipboard (screenshot tool, browser, etc.).
2. In **ask mode**, confirm OCR in the bubble; in **auto**, OCR starts immediately.
3. Image sent to vision API (`ocr.model`); extracted text → TTS pipeline.

Check `ocr.log` in the config directory for OCR output.

### PaddleOCR-VL not available on my provider

Change `ocr.model` to a vision model your endpoint supports, or disable `ocr.enabled`.

## Platform

### Windows 11 antivirus blocks hotkeys

Whitelist Python or `SpeakHelper.exe`. `pynput` hooks keyboard globally.

### Second instance says already running

By design (single instance). Use system tray icon; kill stale process from Task Manager if needed.

### Linux Wayland hotkey issues

Wayland limits global hotkeys; try X11 session or check distro notes for `pynput`.

## Development & search keywords

**English:** text-to-speech, TTS, read aloud, clipboard reader, hotkey TTS, Edge TTS, OpenAI speech API, OCR to speech, PySide6, Qt desktop, accessibility helper.

**中文:** 文字转语音, 朗读助手, 剪贴板朗读, 选中朗读, 识图朗读, 全局快捷键, Edge TTS, 无障碍朗读.

See also: [Installation](installation.md), [Configuration](configuration.md), [Architecture](architecture.md).
