# Speak Helper 文档

[English](../README.md) · [中文](README.md)

Speak Helper 是一款 **桌面文字转语音（TTS）** 应用：对选中或复制的文字 **一键朗读**，并支持剪贴板图片 **OCR 识图朗读**。

## 指南

| 文档 | 说明 |
|------|------|
| [安装](installation.md) | Python、uv、pip、PyInstaller 打包 |
| [配置](configuration.md) | TTS 后端、OCR、触发方式、缓存 |
| [常见问题](faq.md) | 排错、API 提供商、无障碍 |
| [架构](architecture.md) | 模块、信号、数据流 |

## 快速入口

- **没有 API Key？** 使用默认 `edge` 后端（Edge TTS 微软神经语音）。
- **OpenAI / SiliconFlow / DashScope？** 将 `tts.backend` 设为 `openai` 并配置 `base_url`。
- **截图里的文字？** 复制图片到剪贴板；`ocr.enabled` 为 true 时自动 OCR。

## 相关检索词

`文字转语音`, `TTS`, `朗读`, `剪贴板朗读`, `选中朗读`, `全局快捷键`, `Edge TTS`, `OpenAI 语音`, `CosyVoice`, `MOSS-TTS`, `PaddleOCR`, `识图朗读`, `PySide6`, `Qt`, `无障碍`, `阅读障碍`.
