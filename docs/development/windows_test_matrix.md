# Windows validation matrix

Last updated: 2026-09-10

Use this matrix for both development builds and packaged releases. Record facts,
not assumptions. A passing service-level probe does not replace the application
tests below.

## Current environment

- OS: Windows 11
- Python: 3.12.10
- Qt/PySide6: 6.11.1
- Build types: development environment (`uv run`) and standalone PyInstaller folder
- Default Read Selection hotkey: registration failed with Windows error 1409
  because another application owns `Ctrl+Alt+R` on this host.
- Native registrar probe: `Ctrl+Alt+Shift+F24` registered and unregistered.
- Shortcut suggestion probe: `Ctrl+Alt+Space` is currently available on this host.

## Automated and integration evidence

| Scenario | Result | Evidence |
| --- | --- | --- |
| Native hotkey registration and cleanup | PASS | Uncommon probe chord registered with `RegisterHotKey`, then unregistered |
| Hotkey conflict reporting | PASS | Default chord returned Windows error 1409 and emitted a structured error event |
| Available shortcut suggestion | PASS | Native probe skipped occupied `Ctrl+Alt+R` and selected `Ctrl+Alt+Space` |
| Held shortcut modifiers | UNIT PASS | Copy waits on native key state; timeout and release transitions covered |
| Repeated selection capture | PASS | `scripts/windows_selection_probe.py`: 10/10 consecutive cycles |
| Unicode and French accents | PASS | Probe captured `français — Unicode ✓` exactly |
| Clipboard restoration | PASS | Unit tests cover text restoration; the 10-cycle probe ran with restoration enabled |
| Same text selected twice | PASS | Sequence-number unit test does not rely on text inequality |
| Empty/no-copy timeout | PASS | Deterministic unit test |
| Edge-TTS English synthesis | PASS | Live MP3 response, 13,968 bytes |
| Edge-TTS French synthesis | PASS | Live MP3 response, 12,096 bytes |
| Qt audio playback | PASS | Real MP3 emitted playback started and finished; file handle released afterward |
| Packaged Edge-TTS and playback | PASS | `SpeakHelper.exe --tts-probe` exited 0 |
| English Settings layout | PASS | Native Windows render inspected at 860 x 700 |
| French Settings layout | PASS | Native Windows render inspected at 860 x 700 |
| Settings scaling | PASS | Every EN/FR light/dark page passes at 100% and 150% Qt scaling |

The 2026-09-10 rerun was correctly inconclusive because the foreground surface was
Windows `LockApp`: `SendInput` was rejected and no synthetic hotkey could reach the
application. The probe now reports hotkey triggers, capture starts, and captured text
separately, and supports `--capture-only` to isolate the Copy transaction. Rerun both
modes only in an unlocked interactive desktop session.

## Application matrix

| Application / scenario | Development | Packaged | Notes |
| --- | --- | --- | --- |
| PyCharm / selected Codex response | NOT RUN | NOT RUN | Required release acceptance test |
| Chrome | NOT RUN | NOT RUN | Test short, long, and multiline selections |
| Edge | NOT RUN | NOT RUN | Test short, long, and multiline selections |
| Notepad | NOT RUN | NOT RUN | Test ten consecutive reads |
| Word or equivalent | NOT RUN | NOT RUN | Include delayed clipboard rendering |
| PDF viewer | NOT RUN | NOT RUN | Include multiline text and ligatures |
| Terminal with copy support | NOT RUN | NOT RUN | Application must own the Copy shortcut |
| Empty selection | UNIT PASS | NOT RUN | Must show a localized timeout/error |
| Long Markdown and code blocks | UNIT PASS | NOT RUN | Code is preserved by default |
| Stop current speech | DEV PASS | NOT RUN | Unit state test plus real playback stop/source release |
| Pause and resume | UNIT PASS | NOT RUN | State follows Qt multimedia signals |
| Replay last text | UNIT PASS | NOT RUN | Composition path implemented |
| English/French runtime switch | DEV PASS | LAYOUT PASS | Dialog tests and native renders |
| Single instance | DEV SMOKE | NOT RUN | Packaged behavior still required |

## Critical PyCharm acceptance procedure

Repeat the following at least ten times with the packaged build:

1. Select a complete Codex response in PyCharm.
2. Press the configured Read Selection hotkey.
3. Verify that audio starts and matches the selection.
4. Press Stop and verify immediate silence.
5. Select a different response and read it immediately.
6. Confirm that obsolete audio is not queued.
7. Confirm that the clipboard content present before step 1 is restored.

Do not mark Mission 18 or release readiness complete until this passes repeatedly.
