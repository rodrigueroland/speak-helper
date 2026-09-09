# Upstream audit

Audit date: 2026-09-09  
Upstream: `https://github.com/archoor/speak-helper`  
Audited commit: `b348a08` (`fix: bundle edge-tts correctly in Windows build`)  
Release version: `0.0.1`

## Baseline validation

- Environment: Windows, CPython 3.12.10, uv 0.12.9, PySide6 6.11.1.
- `uv sync --extra dev`: passed.
- First `uv run pytest -ra`: 5 passed and 5 setup errors because the user's
  global pytest temporary directory was not readable (`WinError 5`). This was
  an environment failure before test logic ran.
- `uv run pytest -ra --basetemp .pytest-baseline-temp`: 10 passed in 0.57 s.
- Application smoke launch: `python -m speak_helper` remained alive for three
  seconds with the Qt offscreen platform and was then terminated by the audit
  harness. This establishes that imports and startup complete; it does not
  validate tray interaction, hotkeys, TTS, or audio output.
- The upstream packaged executable was not built during the baseline audit.

## Architecture

The package is a small signal-wired PySide6 application. `SpeakHelperApp` is
the composition root and also contains application workflow decisions. Most
services are `QObject` implementations that depend directly on `Config` and Qt
types. There are no explicit interfaces between the application policy and its
clipboard, hotkey, network, or audio adapters.

Primary modules:

- `main.py`: application startup, Windows single-instance mutex, object
  construction, signal wiring, mode handling, speech orchestration, and quit.
- `config.py`: JSON configuration merged over a global default dictionary,
  optional `.env` fallback, API key retrieval, and cache directory creation.
- `clipboard_watcher.py`: observes `QClipboard.dataChanged` and emits text or
  image signals.
- `hotkey_service.py`: registers a `pynput.GlobalHotKeys` listener, simulates
  Ctrl+C, reads the clipboard, and emits selected text.
- `text_filter.py`: debounce, minimum/maximum length, and hash-based dedup.
- `speech_service.py`: sentence splitting, chunking, Edge or OpenAI-compatible
  synthesis, cache lookup/eviction, and QThread lifecycle.
- `audio_player.py`: `QMediaPlayer` wrapper with a FIFO chunk queue.
- `ocr_service.py`: QImage conversion and an OpenAI-compatible vision request.
- `ui/`: floating dock, prompt bubble, tray menu, and a single large settings
  dialog.

## Startup flow

1. `python -m speak_helper` imports and calls `speak_helper.main.main()`.
2. A `QApplication` is created and configured not to exit when the last window
   closes.
3. Windows creates a named global mutex. Other platforms have no single-instance
   implementation. Mutex failures are silently treated as success.
4. `SpeakHelperApp` eagerly creates configuration, TTS, player, filter,
   clipboard watcher, hotkey service, OCR service, floating widgets, and tray.
5. Signals are wired directly in the controller and the hotkey listener starts.
6. The Qt event loop runs. There is no startup health summary or structured log.

## UI architecture

- `FloatingDock` is a custom-painted always-on-top widget. It saves its position
  directly through `Config` and emits click/double-click/right-click signals.
- `PromptBubble` is a custom frameless dialog with hard-coded dimensions,
  colors, Chinese strings, and a countdown timer.
- `TrayIcon` constructs the menu, holds state, and exposes action signals. The
  main controller reaches into its private `_menu` attribute.
- `SettingsDialog` is a 708-line class that constructs all pages, reads/writes
  configuration, makes backend test calls, manages worker threads, clears the
  cache, and owns all styling. It contains a Python worker thread that mutates
  Qt widgets directly, which violates Qt thread-affinity rules.
- User-facing strings are hard-coded across widgets and the controller. There
  is no localization boundary or runtime retranslation strategy.

## TTS and audio flow

`SpeechService.speak()` cancels the current pipeline, splits text on paragraph
and Chinese/English sentence punctuation, groups sentences, creates a QThread,
and runs `_PipelineWorker`. Each synthesized chunk is emitted to
`AudioPlayer.enqueue()`. The player starts the first available chunk and moves
to the next on `EndOfMedia`.

Edge uses `edge_tts.Communicate.save()` through a private asyncio loop in the
worker thread. OpenAI-compatible synthesis posts to `/audio/speech` with a
mandatory Authorization header. Responses are not validated for content type,
minimum length, or supported encoding before being cached.

`AudioPlayer` supports stop and queue reset, but has no pause/resume API. The
floating dock's pause action pauses input monitoring, not current audio. A new
speech request resets the player queue, but cancellation cannot interrupt an
in-flight synchronous HTTP or Edge request; old chunks can therefore race into
a newer playback session. Temporary uncached audio files are not deleted.

## Hotkey and selected-text flow

`pynput.GlobalHotKeys` recognizes the configured chord on a listener thread and
emits an internal Qt signal. The main-thread slot saves only clipboard text and
starts a Python thread. That thread sleeps 80 ms, simulates Ctrl+C, and calls
`QTimer.singleShot(160, callback)` to read and restore clipboard text.

### Likely direct cause of Ctrl+Alt+R doing nothing on Windows

The delayed Qt callback is scheduled from a plain Python thread. That thread
does not run a Qt event loop, so its `QTimer.singleShot` callback is not reliably
delivered. Consequently `_read_and_restore()` may never execute and
`text_ready` is never emitted. This conclusion follows directly from the code's
thread/timer ownership and is the highest-confidence failure mechanism.

Additional reliability problems:

- Registration success is assumed as soon as the pynput listener thread starts;
  no positive status or conflict detection is exposed.
- The fixed 160 ms delay is too short for delayed clipboard providers and has
  no retry or clipboard sequence-number check.
- A repeated selection identical to the old clipboard is discarded.
- Only prior text is remembered; images, rich text, files, and empty clipboard
  state are not restored faithfully.
- An empty old clipboard is never restored.
- The regular clipboard watcher sees the simulated copy, which can show a
  prompt or start duplicate speech independently of the hotkey path.
- There is no in-progress guard, request generation, or duplicate-event
  suppression for rapid repeated hotkeys.
- `pynput` hook behavior and copy simulation share one service, preventing a
  native Windows `RegisterHotKey` implementation from being substituted cleanly.

## Clipboard flow

`ClipboardWatcher` listens to Qt's clipboard change signal and classifies local
file lists, browser image-plus-URL payloads, plain text, and images. Text then
passes through `TextFilter`, which debounces with a Qt timer, truncates at 2,000
characters by default, and suppresses the last MD5 hash.

There is no source tagging for application-generated clipboard writes, no
transaction for selected-text capture, and no coordination between the watcher
and hotkey service. The 2,000-character default silently truncates many Codex
responses. Markdown and code are not normalized beyond `.strip()`.

## Configuration

Configuration is JSON under the platform-specific `speak_helper` user config
directory. Defaults are deep-copied, then saved JSON is recursively merged, then
selected environment variables fill fields absent from saved config. There is
no schema version, validation, atomic write, corrupt-file backup, or migration
report. Unknown keys survive only in memory while that file is loaded.

The default backend is Edge but the default voice is Chinese. The default mode
is `ask`, clipboard monitoring and OCR are enabled eagerly, and OpenAI defaults
are provider-specific. The API key is stored in plaintext JSON as the primary
store despite documentation calling it secure; keyring is only a fallback copy.

## Threads and asynchronous behavior

- Qt main thread: UI, clipboard reads, timers, service orchestration.
- Pynput listener thread: global keyboard hook callback.
- Plain Python hotkey helper thread: delayed copy simulation and the incorrectly
  owned Qt single-shot timer.
- TTS QThread: sequential synchronous synthesis calls; Edge creates an asyncio
  loop inside this worker.
- OCR QThread subclass: image conversion and synchronous HTTP request.
- Plain Python Edge test thread: directly updates settings widgets (unsafe).

Shutdown stops pynput and audio, but does not explicitly stop/wait for TTS or OCR
workers. `SpeechService` waits only 500 ms and then drops Python references even
if the underlying request still runs.

## Platform-specific behavior

- Windows: named mutex, pynput Windows backend bundled, build script and icon.
- macOS: a separate shell build script bundles pynput's Darwin backend.
- Linux: runtime is claimed supported, but there is no build script and global
  hotkeys depend on pynput/X11 behavior; Wayland limitations are undocumented.
- Clipboard capture always simulates Ctrl+C, including macOS where Command+C is
  normally required. This makes the documented macOS selection flow doubtful.

## Packaging and CI

Windows uses a PyInstaller one-directory spec and PowerShell build script. The
script syncs dependencies, regenerates the icon, removes previous build output,
builds, and zips `dist/SpeakHelper`. Translation assets do not yet exist. macOS
uses an independent pip-based script rather than the locked uv environment.

CI runs only pytest on Ubuntu/Python 3.13 with Qt offscreen. It does not run a
formatter, linter, type checker, Windows tests, or a packaging smoke build.

## Known weaknesses and technical debt

1. Hotkey-to-clipboard callback is broken by Qt timer thread affinity.
2. Hotkey capture and automatic clipboard monitoring race and can duplicate work.
3. No localization layer; production UI, errors, comments, and internal docs are
   predominantly Chinese.
4. OpenAI-compatible local endpoints are rejected by the controller when no API
   key is configured.
5. Pause does not pause audio; it disables monitoring.
6. Cancellation does not safely isolate stale TTS chunks from new sessions.
7. Settings mixes presentation, network I/O, cache operations, and persistence.
8. Edge backend test performs unsafe cross-thread widget mutations.
9. Diagnostics and structured event logging are absent; OCR logs full extracted
   user content, which violates the target privacy policy.
10. Configuration lacks versioning, validation, atomic persistence, and locale.
11. Clipboard restoration is incomplete and uses fixed sleeps.
12. OCR starts and observes images even though it is secondary functionality.
13. Tests cover only 10 narrow cases and do not characterize hotkeys, clipboard,
    audio state, UI localization, migrations, or error mapping.
14. CI and build metadata still assume upstream product URLs and capabilities.

## Recommended change seams

- A plain configuration model/repository with validation and migration.
- A centralized translation catalog with observable language changes.
- Hotkey registrar ports plus Windows native and pynput adapters.
- A selected-text capture coordinator with clipboard and copy-injection ports.
- A request-generation-aware speech coordinator and backend protocol.
- A small text normalization policy independent of Qt.
- Diagnostics state/event collection separated from the diagnostics widget.
- Thin settings pages backed by shared theme tokens and service-level test APIs.

