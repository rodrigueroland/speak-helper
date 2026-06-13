# Configuration

[English](configuration.md) · [中文](../zh/configuration.md)

Speak Helper stores settings in a JSON file under the user config directory (via `platformdirs`). Copy [config.example.json](../config.example.json) as a reference.

**Optional `.env`:** see [`.env.example`](../.env.example). **Model variables in `.env` are optional** — configure TTS/OCR models in **⚙ Settings** instead. No `.env` required.

**Priority per field:** Settings / `config.json` → `.env` → built-in defaults.

**Config path examples**

| OS | Typical path |
|----|----------------|
| Windows | `%APPDATA%\speak_helper\config.json` |
| macOS | `~/Library/Application Support/speak_helper/config.json` |
| Linux | `~/.config/speak_helper/config.json` |

Most options can be changed in the **Settings** dialog (tray menu).

## TTS backends

### Edge TTS (`tts.backend: "edge"`)

Free **Microsoft neural text-to-speech** via the `edge-tts` library. No API key.

| Key | Default | Description |
|-----|---------|-------------|
| `tts.edge_voice` | `zh-CN-XiaoxiaoNeural` | Neural voice name |
| `tts.speed` | `1.2` | Speed multiplier (maps to Edge `rate`) |

Popular voices: `zh-CN-XiaoxiaoNeural`, `zh-CN-YunxiNeural`, `en-US-JennyNeural`.

**Search terms:** Edge TTS, Microsoft TTS, free TTS, neural voice, 微软语音, 免费朗读.

### OpenAI-compatible (`tts.backend: "openai"`)

Uses HTTP `POST {base_url}/audio/speech` — same shape as **OpenAI TTS API**.

| Key | Description |
|-----|-------------|
| `tts.base_url` | API root, e.g. `https://api.openai.com/v1` |
| `tts.api_key` | Bearer token (also in keyring) |
| `tts.model` | Model id, e.g. `tts-1`, `FunAudioLLM/CosyVoice2-0.5B` |
| `tts.voice` | Voice id, e.g. `nova` or `model:voice` for SiliconFlow |
| `tts.speed` | `0.5` – `2.0` |
| `tts.format` | `mp3`, `opus`, etc. |
| `tts.sentences_per_chunk` | Sentences merged per API call (streaming playback) |
| `tts.timeout_sec` | HTTP timeout |

**Supported providers (change `base_url` only)**

| Provider | Base URL |
|----------|----------|
| OpenAI | `https://api.openai.com/v1` |
| Alibaba DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| SiliconFlow | `https://api.siliconflow.cn/v1` |
| Self-hosted / compatible | Your endpoint |

**Search terms:** OpenAI TTS, CosyVoice, MOSS-TTS, SiliconFlow speech, DashScope TTS, compatible-mode API.

## Triggers (clipboard & hotkey)

| Key | Default | Description |
|-----|---------|-------------|
| `trigger.clipboard_enabled` | `true` | Watch clipboard for text/images |
| `trigger.hotkey_enabled` | `true` | Global hotkey |
| `trigger.hotkey` | `ctrl+alt+r` | Hotkey combo (`pynput` syntax) |
| `trigger.mode` | `ask` | `ask` = prompt bubble; `auto` = speak immediately |
| `trigger.min_length` | `2` | Ignore shorter clipboard text |
| `trigger.max_length` | `2000` | Truncate long text |
| `trigger.debounce_ms` | `200` | Clipboard debounce |

**Hotkey flow:** simulates copy → reads clipboard → TTS. Works with selected text in most apps.

## OCR (clipboard image → speech)

Uses OpenAI-compatible **vision** API with the same `base_url` and `api_key` as TTS.

| Key | Default | Description |
|-----|---------|-------------|
| `ocr.enabled` | `true` | Process clipboard images |
| `ocr.model` | `PaddlePaddle/PaddleOCR-VL-1.5` | Vision model on provider |
| `ocr.image_quality` | `85` | JPEG quality before upload (1–95) |

Log file: `ocr.log` in the config directory.

**Search terms:** OCR to speech, image text reader, screenshot TTS, PaddleOCR-VL, vision API, 识图朗读, 截图朗读.

## UI

| Key | Default | Description |
|-----|---------|-------------|
| `ui.dock_edge` | `right` | Floating dock side: `right` or `left` |
| `ui.bubble_timeout_ms` | `6000` | Ask bubble auto-dismiss |
| `ui.theme` | `system` | `system`, `dark`, `light` |

## Cache

| Key | Default | Description |
|-----|---------|-------------|
| `cache.enabled` | `true` | Cache synthesized audio |
| `cache.max_mb` | `100` | Max cache size; oldest files deleted |

Cache directory: `{config_dir}/cache/`. Clear from Settings UI.

## API key storage

1. Primary: `tts.api_key` in `config.json`
2. Backup: OS keyring (`speak_helper` / `api_key`)

Use [write_api_key.py](../write_api_key.py) for scripted setup if needed.
