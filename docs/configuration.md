# Configuration

Speak Helper stores `config.json`, cache files, and rotating logs in the
platform-specific user configuration directory. Diagnostics displays the exact
paths. `SPEAK_HELPER_CONFIG_DIR` overrides the directory for tests and controlled
deployments.

The current schema is version 2. Older dictionaries are deep-merged with defaults,
then validated. Missing `ui.language` uses the first-launch OS locale (`fr` for a
French locale, otherwise `en`).

## Important keys

| Key | Default | Meaning |
| --- | --- | --- |
| `ui.language` | locale-derived | `en` or `fr` |
| `ui.autostart` | `false` | Launch at Windows user sign-in |
| `trigger.mode` | `manual` | `manual`, `ask`, or `auto` |
| `trigger.hotkey` | `ctrl+alt+r` | Read Selection chord |
| `trigger.stop_hotkey` | `ctrl+alt+shift+x` | Stop chord |
| `clipboard.restore_after_capture` | `true` | Restore prior MIME clipboard data |
| `clipboard.capture_timeout_ms` | `1500` | Selection-copy deadline |
| `tts.backend` | `edge` | `edge` or `openai` |
| `tts.edge_voice` | `en-US-AriaNeural` | Edge voice identifier |
| `tts.base_url` | `http://127.0.0.1:8000/v1` | Compatible API root |
| `tts.api_key` | empty | Optional bearer token |
| `tts.timeout_sec` | `30` | Request timeout |
| `preprocessing.preserve_code` | `true` | Keep fenced code |
| `preprocessing.url_mode` | `keep` | `keep`, `domain`, or `omit` |
| `ocr.enabled` | `false` | Enable optional image OCR |

Use [config.example.json](../config.example.json) as a complete safe example.

## OpenAI-compatible and Qwen

The generic backend posts JSON to `{base_url}/audio/speech` with model, input,
voice, speed, and response format. Authorization is sent only when the API key is
non-empty. The Qwen3 preset changes editable defaults but uses this same transport.
The desktop process never imports a Qwen, CUDA, or PyTorch package.

The Qwen3 preset defaults to `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` with voice
`Vivian`. It adds `language: English` or `language: French` to the otherwise
standard OpenAI speech payload. Custom providers receive only the standard fields.

Environment variables remain supported as fallbacks when the corresponding value
was not explicitly saved. Prefer the Settings UI for normal use.
