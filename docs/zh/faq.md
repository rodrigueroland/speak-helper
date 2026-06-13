# 常见问题 FAQ

[English](../faq.md) · [中文](faq.md)

关于 **Speak Helper** 桌面 **文字转语音（TTS）**、**朗读**、**剪贴板朗读**、**识图朗读** 的常见问题。

## 概述

### Speak Helper 是什么？

基于 **PySide6** 的轻量桌面应用，通过 **TTS** **朗读文字**。支持 **剪贴板复制**、**全局快捷键**（`Ctrl+Alt+R`）、**剪贴板图片**（OCR 后朗读）。

### 谁适合用 Speak Helper？

详见 [使用场景](use-cases.md)。简要来说：

- **不想看字** — 累了、文档长、想边做事边听。
- **视力 / 阅读辅助** — 视力不佳、视疲劳、老年人、阅读障碍（针对 **复制/选中** 的文字，非全盘读屏）。
- **学习与识图** — 练听力、截图文字朗读。

### 它是读屏软件吗？

不是完整的 **无障碍读屏**（如 NVDA、VoiceOver），而是 **朗读辅助工具**，适合 **低视力听内容**、**阅读障碍**、**多任务**、**语言学习** 等场景（需主动复制或选中文字）。

### 能完全离线吗？

- **Edge 后端**：合成需联网访问微软 Edge TTS；无需 API Key。
- **OpenAI 兼容后端**：需访问您配置的 API。
- **界面与缓存**：本地；已缓存音频可离线重播。

## TTS 与 API

### 选哪个 TTS 后端？

| 需求 | 后端 |
|------|------|
| 免费、无需 Key、中文效果好 | `edge` |
| 自定义模型（CosyVoice、MOSS-TTS、OpenAI） | `openai` |

### OpenAI TTS、Edge TTS、CosyVoice 怎么选？

- **OpenAI `tts-1`**：稳定付费，英文音色为主。
- **Edge TTS**：免费神经语音（如 `zh-CN-XiaoxiaoNeural`）。
- **CosyVoice / MOSS-TTS**（SiliconFlow 等）：开源模型 + 兼容 `/audio/speech`。

### 快捷键按了没声音？

1. 确认已 **选中文字**。
2. 检查托盘：未暂停、热键与剪贴板已启用。
3. macOS 需授予 **辅助功能** 权限。
4. 部分应用禁止模拟 Ctrl+C。

### API 报错 / 401 / 超时

- 确认 `base_url` 格式正确（通常以 `/v1` 结尾）。
- 在设置中检查 API Key。
- 慢模型可增大 `tts.timeout_sec`。
- SiliconFlow 音色常为 `model:voice_name` 格式。

## 剪贴板与 OCR

### 复制触发太频繁 / 重复朗读

- 默认 **询问模式** 会弹气泡；可在托盘改为 **自动**。
- **去重** 会忽略连续相同剪贴板内容。
- 可调整 `trigger.debounce_ms`、`trigger.min_length`。

### 截图 / 图片如何朗读？

1. 将图片复制到剪贴板。
2. **询问模式** 在气泡确认；**自动模式** 直接 OCR。
3. Vision API（`ocr.model`）提取文字 → TTS。

OCR 结果见配置目录下 `ocr.log`。

### 提供商没有 PaddleOCR-VL

将 `ocr.model` 改为您端点支持的视觉模型，或关闭 `ocr.enabled`。

## 平台

### Windows 11 杀毒拦截热键

将 Python 或 `SpeakHelper.exe` 加入白名单；`pynput` 会全局挂钩键盘。

### 提示已在运行

单实例设计；查看系统托盘。必要时在任务管理器结束残留进程。

### Linux Wayland 热键无效

Wayland 限制全局热键；可尝试 X11 或查阅 `pynput` 说明。

## 检索关键词

**英文：** text-to-speech, TTS, read aloud, clipboard reader, Edge TTS, OpenAI speech, OCR to speech, PySide6, accessibility.

**中文：** 文字转语音, 朗读助手, 剪贴板朗读, 选中朗读, 识图朗读, 全局快捷键, 无障碍朗读.

另见：[安装](installation.md)、[配置](configuration.md)、[架构](architecture.md)。
