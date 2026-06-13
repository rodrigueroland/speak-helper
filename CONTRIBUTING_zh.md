# 参与贡献 Speak Helper

[English](CONTRIBUTING.md) · [中文](CONTRIBUTING_zh.md)

感谢为这款 **文字转语音**、**剪贴板朗读**、**识图朗读** 桌面工具做出贡献。

## 开发环境

```powershell
cd speak_helper
uv venv
uv sync --all-extras
uv run pytest tests/
```

要求：Python 3.11+，带图形界面的 Windows / macOS / Linux（PySide6）。

## 代码风格

- 遵循现有结构：业务逻辑在 `speak_helper/`，界面在 `speak_helper/ui/`
- 新 Python 文件使用 `from __future__ import annotations`
- 单次 PR 保持改动聚焦，避免无关重构
- 界面文案可暂用中文；用户文档需同步更新 `docs/`（英文）与 `docs/zh/`（中文）

## PR 检查清单

- [ ] `uv run pytest tests/` 通过
- [ ] 新配置项写入 `config.py` 的 `DEFAULT` 与 `config.example.json`
- [ ] 用户可见变更同步 `docs/` 与 `docs/zh/`
- [ ] 更新 `CHANGELOG.md`

## 提交 Issue

请包含：

- 操作系统（如 Windows 11、macOS 14）
- Python 版本
- TTS 后端（`edge` 或 `openai`）及 API 地址
- 复现步骤（剪贴板 / 快捷键 / OCR）
- 相关日志：Windows 下 OCR 日志位于 `%APPDATA%\speak_helper\ocr.log`

## 安全

API Key 泄露请勿公开 Issue，见 [SECURITY.md](SECURITY.md)。
