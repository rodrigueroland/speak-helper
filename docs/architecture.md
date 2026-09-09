# Architecture

`SpeakHelperApp` is the composition root. It creates services and connects Qt
signals; individual widgets do not own hotkey, clipboard, HTTP, or playback policy.

```text
Windows RegisterHotKey / pynput fallback
                |
                v
      SelectionCaptureService ---- ClipboardWatcher
                |                         |
                +----------+--------------+
                           v
               conservative normalization
                           |
                           v
                    SpeechService
                  /               \
             Edge-TTS       OpenAI-compatible HTTP
                  \               /
                           v
                     AudioPlayer
                           |
                      tray + dock
```

## Main boundaries

- `config.py`: versioned JSON configuration, locale defaulting, validation, and
  backward-compatible deep merge.
- `i18n.py`: observable centralized English/French catalogs.
- `hotkey_service.py`: parsing and registrar interface; native Windows
  `RegisterHotKey` and cross-platform `pynput` fallback.
- `selection_capture.py`: clipboard transaction and platform Copy injection.
- `clipboard_watcher.py`: optional user clipboard monitoring, suppressible during
  internal capture operations.
- `text_normalizer.py`: independently testable, conservative speech preprocessing.
- `speech_service.py`: chunking, caching, backend calls, cancellation generations.
- `audio_player.py`: sequential Qt Multimedia playback and state transitions.
- `diagnostics.py` and `logging_config.py`: safe diagnostics and rotating JSON Lines.
- `ocr_service.py`: optional isolated vision request; disabled by default.
- `ui/`: presentation widgets and semantic style tokens.

## Thread model

Qt widgets, native hotkey filtering, clipboard reads, and orchestration live on the
main Qt thread. TTS and OCR requests run in owned worker threads and return via Qt
signals. A new speech request increments a generation and cancels old workers, so
late responses cannot enter the current playback queue. Shutdown cancels workers,
waits for outstanding network calls, stops media, unregisters hotkeys, and releases
the Windows mutex.

## Windows selection transaction

`RegisterHotKey` posts `WM_HOTKEY` into the Qt message loop. The service queues an
action signal on the Qt thread. Selection capture snapshots all MIME formats, notes
`GetClipboardSequenceNumber`, injects one `SendInput` Ctrl+C batch, and polls for a
new sequence until text appears or the configured deadline expires. Restoration is
performed while the normal clipboard watcher is suppressed.

## Extension points

Keep new backends behind the synthesis service and model them as configuration
presets when they share the OpenAI-compatible contract. Keep platform-specific
hotkeys and Copy injection behind their existing protocols. Add all visible text to
both translation catalogs; logs remain English.
