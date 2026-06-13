# 配置说明

[English](../configuration.md) · [中文](configuration.md)

Speak Helper 在用户配置目录保存 JSON 设置。可参考 [config.example.json](../../config.example.json)。

**可选 `.env`：** 见 [`.env.example`](../../.env.example)。**`.env` 中的模型配置为可选**，TTS/OCR 模型可在 **⚙ 设置** 中配置，无需写入 `.env`。

**每项优先级：** 设置面板 / `config.json` → `.env` → 内置默认值。

**配置路径示例**

| 系统 | 路径 |
|------|------|
| Windows | `%APPDATA%\speak_helper\config.json` |
| macOS | `~/Library/Application Support/speak_helper/config.json` |
| Linux | `~/.config/speak_helper/config.json` |

多数选项可在托盘 **设置** 对话框中修改。

## TTS 后端

### Edge TTS（`tts.backend: "edge"`）

通过 `edge-tts` 使用 **微软神经语音**，**无需 API Key**。

| 键 | 默认值 | 说明 |
|----|--------|------|
| `tts.edge_voice` | `zh-CN-XiaoxiaoNeural` | 神经语音名称 |
| `tts.speed` | `1.2` | 语速倍率 |

常用音色：`zh-CN-XiaoxiaoNeural`、`zh-CN-YunxiNeural`、`en-US-JennyNeural`。

**检索词：** Edge TTS、微软语音、免费朗读、神经语音。

### OpenAI 兼容（`tts.backend: "openai"`）

HTTP `POST {base_url}/audio/speech`，与 **OpenAI TTS API** 兼容。

| 键 | 说明 |
|----|------|
| `tts.base_url` | API 根地址 |
| `tts.api_key` | Bearer 令牌（亦可存 keyring） |
| `tts.model` | 模型，如 `tts-1`、`FunAudioLLM/CosyVoice2-0.5B` |
| `tts.voice` | 音色，SiliconFlow 格式为 `model:voice` |
| `tts.speed` | `0.5` – `2.0` |
| `tts.format` | `mp3`、`opus` 等 |
| `tts.sentences_per_chunk` | 每块合并句数（边下边播） |
| `tts.timeout_sec` | HTTP 超时 |

**支持的提供商（改 Base URL 即可）**

| 提供商 | Base URL |
|--------|----------|
| OpenAI | `https://api.openai.com/v1` |
| 阿里 DashScope | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| SiliconFlow | `https://api.siliconflow.cn/v1` |
| 自建 / 其他兼容 | 对应地址 |

**检索词：** OpenAI TTS、CosyVoice、MOSS-TTS、SiliconFlow 语音、DashScope TTS、兼容模式 API。

## 触发方式（剪贴板与热键）

| 键 | 默认值 | 说明 |
|----|--------|------|
| `trigger.clipboard_enabled` | `true` | 监听剪贴板文字/图片 |
| `trigger.hotkey_enabled` | `true` | 全局快捷键 |
| `trigger.hotkey` | `ctrl+alt+r` | 组合键（`pynput` 语法） |
| `trigger.mode` | `ask` | `ask` 询问气泡；`auto` 自动朗读 |
| `trigger.min_length` | `2` | 最短文字长度 |
| `trigger.max_length` | `2000` | 最大长度（超出截断） |
| `trigger.debounce_ms` | `200` | 剪贴板防抖 |

**热键流程：** 模拟复制 → 读取剪贴板 → TTS。适用于多数应用的选中文字。

## OCR（剪贴板图片 → 语音）

使用与 TTS 相同的 `base_url`、`api_key`，调用 **Vision** 兼容接口。

| 键 | 默认值 | 说明 |
|----|--------|------|
| `ocr.enabled` | `true` | 处理剪贴板图片 |
| `ocr.model` | `PaddlePaddle/PaddleOCR-VL-1.5` | 视觉模型 |
| `ocr.image_quality` | `85` | 上传前 JPEG 质量 |

日志：`ocr.log`（配置目录下）。

**检索词：** 识图朗读、截图朗读、OCR 转语音、PaddleOCR-VL、Vision API。

## 界面

| 键 | 默认值 | 说明 |
|----|--------|------|
| `ui.dock_edge` | `right` | 浮动条位置 `right` / `left` |
| `ui.bubble_timeout_ms` | `6000` | 询问气泡超时 |
| `ui.theme` | `system` | `system` / `dark` / `light` |

## 缓存

| 键 | 默认值 | 说明 |
|----|--------|------|
| `cache.enabled` | `true` | 缓存合成音频 |
| `cache.max_mb` | `100` | 上限，超出删最旧文件 |

缓存目录：`{config_dir}/cache/`，可在设置中清空。

## API Key 存储

1. 主存储：`config.json` 中的 `tts.api_key`
2. 备份：系统 keyring（`speak_helper` / `api_key`）

脚本写入可使用 [write_api_key.py](../../write_api_key.py)。
