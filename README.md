# Speak Helper

Speak Helper is a Windows-first desktop utility that reads selected text aloud.
Select text in PyCharm, a browser, Word, a PDF viewer, an editor, or another
application that supports Copy, then press a global hotkey.

[Documentation française](docs/fr/README.md) · [License](LICENSE) ·
[Development status](docs/missions/STATUS.md)

This repository is a maintained fork of
[archoor/speak-helper](https://github.com/archoor/speak-helper). It preserves the
upstream Git history and MIT license; see [NOTICE.md](NOTICE.md).

## Current status

The Windows native selection pipeline, English/French UI, Edge-TTS, generic
OpenAI-compatible transport, Qwen3 local preset, diagnostics, and standalone
Windows build are implemented. The automated suite and repeatable native probe
pass. Full packaged acceptance in PyCharm, browsers, Word, PDFs, and terminals is
still tracked as open work in the [Windows test matrix](docs/development/windows_test_matrix.md).

## Quick start

### Standalone Windows build

Download or build the `SpeakHelper` folder and run `SpeakHelper.exe`. Python is
not required on the end user's computer.

On first launch:

1. Open Speak Helper from the system tray.
2. Open **Settings → Speech** and select an Edge English or French voice.
3. Open **Settings → Hotkeys** and confirm the Read Selection shortcut.
4. Select text in another application and press `Ctrl+Alt+R`.

If the shortcut is already owned by another application, Speak Helper displays a
clear error. Choose another combination in Settings.

### Development run

Requirements: Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/).

```powershell
uv sync --extra dev
uv run python -m speak_helper
```

Run every local quality gate:

```powershell
.\scripts\check.ps1
```

To validate synthesis and audio playback end to end with the currently configured
backend, run `SpeakHelper.exe --tts-probe` (or
`uv run python -m speak_helper --tts-probe` in development). Exit code `0` means
that synthesis completed and Qt started and finished playback.

## Default shortcuts

| Action | Shortcut |
| --- | --- |
| Read selected text | `Ctrl+Alt+R` |
| Stop | `Ctrl+Alt+Shift+X` |
| Pause / Resume | `Ctrl+Alt+Shift+P` |
| Replay last text | `Ctrl+Alt+Shift+R` |

All shortcuts are configurable. On Windows, native `RegisterHotKey` registration
detects conflicts and `MOD_NOREPEAT` avoids key-repeat storms.

## How selection capture works

For a manual Read Selection request, Speak Helper:

1. snapshots every available Qt clipboard MIME format;
2. sends Copy to the focused application;
3. waits for the Windows clipboard sequence number to change;
4. captures and conservatively normalizes Unicode text;
5. restores the original clipboard when configured;
6. stops obsolete speech and synthesizes the new selection.

This handles repeated identical selections without comparing clipboard text and
suppresses automatic clipboard monitoring during its own transaction.

## Clipboard modes

- **Manual selection only** is the safe default. Only Read Selection speaks.
- **Ask before reading** watches user clipboard changes and requests confirmation.
- **Read clipboard automatically** speaks user clipboard changes immediately.

Automatic modes are disabled during app-generated Copy and restoration events.

## Languages

The user interface supports English and French. Change language under
**Settings → General**; the visible UI updates immediately and the choice persists.
English is the fallback for unknown or missing locales.

On Windows, **Settings → General** also offers an optional per-user launch at
sign-in setting. It uses the current packaged executable and does not require
administrator privileges.

## TTS backends

### Edge-TTS

Edge-TTS is the default and requires no API key. The Settings voice selector
includes English voices from the US and UK and French voices from France, Belgium,
and Canada. Synthesis uses Microsoft's online Edge speech service.

### OpenAI-compatible

Choose **OpenAI-compatible** for any server implementing:

```text
POST {base_url}/audio/speech
```

Configure the base URL, model, voice, optional API key, timeout, speed, and audio
format. Local endpoints may leave the API key empty. Speak Helper reports refused
connections, timeouts, HTTP failures, empty audio, and unsupported content types.

### Qwen3-TTS Local

Choose **Qwen3-TTS Local** to prefill an editable local OpenAI-compatible endpoint
with the published `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` model and `Vivian`
voice. The desktop app does not install or import PyTorch, CUDA, or Qwen. Run a
Qwen3-TTS server separately and expose an OpenAI-compatible `/audio/speech` route;
then edit URL, model, voice, and timeout to match that server. With this preset,
Speak Helper also sends `language` as `English` or `French` from the selected UI
language.

No third-party server is bundled. See the
[official Qwen3-TTS project](https://github.com/QwenLM/Qwen3-TTS) for models and
isolated environment setup. Compatible server wrappers include
[qwen3_audio_api](https://github.com/second-state/qwen3_audio_api) and
[qwen3-tts-server](https://github.com/malaiwah/qwen3-tts-server); follow the
server project's own requirements and security guidance.

## Playback and text processing

- A new manual reading replaces current and queued audio.
- Pause, Resume, Stop, and Replay are available from global shortcuts and the tray.
- Markdown headings and bullet markers are softened for speech.
- URLs can be kept, reduced to their domain, or omitted.
- Fenced source code is preserved by default and is removed only when configured.
- French accents, Unicode, multiline text, and repeated selections are supported.

## Diagnostics and logs

Open **Settings → Diagnostics** to see the version, OS, language, Read shortcut and
registration state, clipboard watcher, TTS backend/endpoint/model, audio state,
cache path, and log path. You can test clipboard content, copy diagnostics, or open
the log folder.

Logs are rotating JSON Lines records in the user configuration directory. They use
English event names such as `hotkey_triggered`, `text_captured`, and
`playback_started`. API keys, authorization headers, and full clipboard/OCR text
are not logged.

## Troubleshooting

### The hotkey does nothing

1. Open Diagnostics and check **Hotkey registration**.
2. If the shortcut conflicts, choose another chord under **Hotkeys**.
3. Confirm the target application supports `Ctrl+C` for its selection.
4. A normal process cannot inject Copy into an elevated application; run both at
   the same integrity level.
5. Increase the selection timeout for slow or delayed clipboard providers.

### Speech fails

- Use **Test TTS** in Settings.
- For Edge-TTS, verify internet access and choose a listed voice.
- For a local endpoint, verify the URL and that `/audio/speech` is implemented.
- Leave API key empty only when the configured server permits it.
- Check Diagnostics and the structured log for the precise stage that failed.

### Audio does not play

Check the active Windows output device and volume. Speak Helper clears old playback
when a new selection arrives. Unsupported server audio formats are rejected before
playback where possible.

## Build Windows

```powershell
.\scripts\build_win.ps1
```

Outputs:

- `dist\SpeakHelper\SpeakHelper.exe`
- `dist\SpeakHelper-win64.zip`

The folder build contains Python, Qt, multimedia plugins, Edge-TTS, and the icon.
The executable supports `--smoke-test` for bounded packaging validation.

## Architecture

The PySide6 composition root connects focused services:

```text
Windows native hotkey -> SelectionCaptureService -> text normalization
                       -> SpeechService -> AudioPlayer -> tray/dock state
```

The UI does not perform HTTP calls. Windows-native details sit behind hotkey and
copy-injection abstractions, with `pynput` fallbacks retained for macOS/Linux.
See [architecture.md](docs/architecture.md) and the
[upstream audit](docs/development/upstream_audit.md).

## Contributing

Use English for code, names, comments, logs, tests, commits, and internal technical
documentation. User-facing strings belong in the centralized English/French
catalogs. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License and attribution

Speak Helper is distributed under the [MIT License](LICENSE). This fork is derived
from the original Speak Helper project by archoor and retains its history and
copyright notice. No affiliation or endorsement is implied.
