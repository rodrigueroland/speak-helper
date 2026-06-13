# Architecture

[English](architecture.md) · [中文](../zh/architecture.md)

High-level design of the **Speak Helper** TTS desktop application (PySide6 / Qt).

## Module map

```
speak_helper/
├── main.py              SpeakHelperApp — signal wiring, lifecycle
├── config.py            JSON + keyring configuration
├── text_filter.py       Debounce, dedup, length limits
├── clipboard_watcher.py   QClipboard monitoring (text + image)
├── hotkey_service.py      Global hotkey → simulate copy → text
├── speech_service.py      Sentence split, TTS pipeline (edge / openai)
├── ocr_service.py         Vision API for clipboard images
├── audio_player.py        Queue playback (QMediaPlayer)
└── ui/
    ├── floating_dock.py   Edge dock widget + state icons
    ├── prompt_bubble.py   Ask-mode confirmation UI
    ├── tray_icon.py       System tray menu
    └── settings_dialog.py Settings tabs
```

## Data flow

### Clipboard text → speech

```
ClipboardWatcher.text_changed
    → TextFilter (debounce, min/max, dedup)
    → mode == ask ? PromptBubble : SpeechService.speak()
    → split_sentences → chunks
    → _PipelineWorker (per-chunk TTS)
    → chunk_ready → AudioPlayer.enqueue (streaming)
    → playback_finished → UI idle
```

### Hotkey → speech

```
HotkeyService (pynput)
    → simulate Ctrl+C
    → read clipboard text
    → SpeechService.speak()   (bypasses ask/auto mode)
```

### Clipboard image → OCR → speech

```
ClipboardWatcher.image_changed
    → PromptBubble (ask) or OcrService directly (auto)
    → OcrService (vision API, JPEG upload)
    → text_ready → SpeechService.speak()
```

## TTS pipeline

| Step | Component | Notes |
|------|-----------|-------|
| Split | `split_sentences()` | Chinese / English punctuation |
| Chunk | `make_chunks(n)` | `sentences_per_chunk` config |
| Fetch | `_ChunkWorker` | `edge` → `edge-tts`; `openai` → httpx POST |
| Cache | SHA1 key in `cache_dir` | Evict by total MB |
| Play | `AudioPlayer` | Sequential queue per speak session |

## Threading model

- **Main thread**: Qt UI, signals/slots
- **Hotkey thread**: `pynput` listener
- **TTS thread**: `QThread` + `_PipelineWorker` (sequential chunk fetch)
- **Edge TTS**: `asyncio.run` inside worker thread per chunk

## Configuration lifecycle

1. `Config()` loads `DEFAULT` merged with `config.json`
2. Settings dialog writes values + `api_key` setter
3. `reload()` after save; `HotkeyService` restarted if hotkey changed

## Single instance (Windows)

`CreateMutexW("Global\\SpeakHelper_SingleInstance_Mutex")` in `main.py` before app loop.

## External dependencies

| Package | Role |
|---------|------|
| PySide6 | GUI, clipboard, media playback |
| httpx | OpenAI-compatible TTS + OCR HTTP |
| edge-tts | Microsoft neural TTS |
| pynput | Global hotkey, key simulation |
| keyring | API key storage |
| platformdirs | Cross-platform config paths |
| Pillow | Image encoding for OCR |

## Extension points

- New TTS backend: add branch in `_ChunkWorker._fetch()` and Settings UI
- New trigger: emit text into `TextFilter.feed` or `SpeechService.speak`
- Replace OCR: adjust `OcrService` prompt and API payload
