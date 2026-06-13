# Speak Helper

**选中文字，一键朗读** — 轻量级桌面 **文字转语音（TTS）** 助手，支持 **Windows**、**macOS**、**Linux**。

[English](README.md) · [中文](README_zh.md)

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **别名 / 搜索词：** 剪贴板朗读、选中朗读、屏幕朗读、识图朗读、OpenAI TTS 客户端、Edge TTS 桌面版、文字转语音、读屏辅助、无障碍朗读。

## 使用场景

当你 **不想盯着文字看、看字吃力，或更适合用耳朵接收信息** 时，Speak Helper 可以把屏幕上的文字转成语音。

### 不想看字，想听内容

| 场景 | 举例 |
|------|------|
| **累了不想读** | 下班后用听的代替看：文章、邮件、聊天记录 |
| **长文档** | 报告、说明书分段复制，边听边休息 |
| **字号小、排版密** | 从任意软件复制文字，用朗读减轻用眼 |

### 视力与阅读辅助

| 场景 | 举例 |
|------|------|
| **视力不佳 / 低视力** | 在浏览器、PDF、桌面软件里选中或复制文字后收听（辅助听内容，**不能替代**专业读屏软件的全局导航） |
| **视疲劳、用眼过度** | 减少长时间盯屏，改听 copied 段落 |
| **老年用户** | 家人可帮忙设好快捷键；复制短信、新闻片段即可清晰收听 |
| **阅读障碍** | 听觉与文字同步，降低纯视觉阅读压力 |

> **说明：** Speak Helper 是 **朗读辅助工具**，针对你主动复制或选中的内容，**不是** NVDA、VoiceOver 那样的完整读屏。可与读屏软件 **搭配使用**，也适合偶尔「听一段」的场景。

### 日常效率

| 场景 | 举例 |
|------|------|
| **多任务** | 边写代码、做饭、运动、通勤时听内容 |
| **语言学习** | 中文 / 英文神经语音，练听力、跟读 |
| **截图 / 图片文字** | 复制截图 → OCR 识图 → 自动朗读 |
| **低打扰** | `Ctrl+Alt+R` 朗读选中文字，无需浏览器插件 |

## 功能

- **屏幕边缘浮动图标**：监听中 / 朗读中 / 已暂停 / 错误 四种状态
- **剪贴板触发**：复制文字后弹气泡询问或直接朗读
- **全局快捷键**：`Ctrl+Alt+R` 朗读当前选中文字
- **询问 / 自动两种模式**：托盘菜单随时切换
- **双 TTS 后端**
  - **Edge TTS**（微软神经语音，无需 API Key）
  - **OpenAI 兼容 API**（`/audio/speech`）— OpenAI、DashScope、SiliconFlow、自建
- **剪贴板图片 OCR**：Vision API 提取文字后朗读（如 PaddleOCR-VL）
- **流式播放**：分句切块，边请求边播放
- **本地音频缓存**：相同文字不重复请求
- **API Key 安全存储**：系统密钥环 + 配置文件
- **单实例运行**：Windows 命名 Mutex

## 快速开始

### 安装

```powershell
cd speak_helper
uv venv
uv sync
```

或使用 pip：

```bash
pip install -r requirements.txt
```

### 运行

```bash
uv run python -m speak_helper
```

首次运行：右击 **系统托盘** → **设置** → 选择 TTS 后端并填写 API Key（OpenAI 兼容模式需要）。

### 默认后端

| 后端 | API Key | 说明 |
|------|---------|------|
| `edge`（默认） | 不需要 | 使用 `edge-tts` / 微软神经语音 |
| `openai` | 需要 | 任意 OpenAI 兼容 `/audio/speech` 端点 |

完整配置见 [docs/zh/configuration.md](docs/zh/configuration.md)。

**可选 `.env`：** 复制 [`.env.example`](.env.example) 作团队默认。**`.env` 中的模型为可选**，可在 ⚙ 设置中配置。优先级：`config.json` → `.env` → 内置默认。

## 快捷键

| 操作 | 快捷键 |
|------|--------|
| 朗读选中文字 | `Ctrl+Alt+R` |
| 气泡确认朗读 | `Enter` |
| 气泡取消 | `Esc` |
| 暂停/继续监听 | 单击浮动图标 |
| 重读上一条 | 双击浮动图标 |

## 打包为可执行文件

**Windows**

```powershell
.\scripts\build_win.ps1
# 产物：dist\SpeakHelper\SpeakHelper.exe
```

**macOS**

```bash
bash scripts/build_mac.sh
# 产物：dist/SpeakHelper.app
```

## 文档

| 主题 | English | 中文 |
|------|---------|------|
| 索引 | [docs/README.md](docs/README.md) | [docs/zh/README.md](docs/zh/README.md) |
| 安装 | [docs/installation.md](docs/installation.md) | [docs/zh/installation.md](docs/zh/installation.md) |
| 配置 | [docs/configuration.md](docs/configuration.md) | [docs/zh/configuration.md](docs/zh/configuration.md) |
| 常见问题 | [docs/faq.md](docs/faq.md) | [docs/zh/faq.md](docs/zh/faq.md) |
| 使用场景 | [docs/use-cases.md](docs/use-cases.md) | [docs/zh/use-cases.md](docs/zh/use-cases.md) |
| 架构 | [docs/architecture.md](docs/architecture.md) | [docs/zh/architecture.md](docs/zh/architecture.md) |

## 运行测试

```bash
uv run pytest tests/
```

## 项目结构

```
speak_helper/
├── speak_helper/          # Python 主包
│   ├── main.py            # 应用控制器
│   ├── config.py          # JSON 配置 + keyring
│   ├── speech_service.py  # TTS（edge + OpenAI 兼容）
│   ├── ocr_service.py     # 剪贴板图片 OCR
│   ├── clipboard_watcher.py
│   ├── hotkey_service.py
│   ├── audio_player.py
│   └── ui/                # PySide6 界面
├── docs/                  # 用户与贡献者文档
├── scripts/               # 打包脚本
├── tests/
├── pyproject.toml
└── config.example.json
```

## 隐私说明

- 文本仅发送至您配置的 **TTS / OCR API**（`edge` 后端使用微软 Edge TTS）。
- 无第三方统计或中转服务。
- API Key 优先存入系统密钥环。
- 本地缓存在用户配置目录，可在设置中一键清空。

## 参与贡献

见 [CONTRIBUTING_zh.md](CONTRIBUTING_zh.md)（[English](CONTRIBUTING.md)）。

## 许可证

[MIT License](LICENSE)

## 搜索关键词

`text-to-speech`, `TTS`, `read aloud`, `clipboard reader`, `Edge TTS`, `OpenAI speech`, `CosyVoice`, `MOSS-TTS`, `OCR to speech`, `PaddleOCR`, `accessibility`, `文字转语音`, `朗读助手`, `剪贴板朗读`, `选中朗读`, `识图朗读`, `全局快捷键`, `PySide6`, `Qt 桌面应用`.
