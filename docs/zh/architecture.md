# 架构说明

[English](../architecture.md) · [中文](architecture.md)

**Speak Helper** 桌面 TTS 应用（PySide6 / Qt）的高层设计。

## 模块一览

```
speak_helper/
├── main.py              SpeakHelperApp — 信号装配与生命周期
├── config.py            JSON + keyring 配置
├── text_filter.py       防抖、去重、长度过滤
├── clipboard_watcher.py 剪贴板监听（文字 + 图片）
├── hotkey_service.py    全局热键 → 模拟复制 → 文字
├── speech_service.py    分句、TTS 流水线（edge / openai）
├── ocr_service.py       剪贴板图片 Vision OCR
├── audio_player.py      播放队列（QMediaPlayer）
└── ui/
    ├── floating_dock.py   边缘浮动条与状态图标
    ├── prompt_bubble.py   询问模式确认气泡
    ├── tray_icon.py       系统托盘菜单
    └── settings_dialog.py 设置面板
```

## 数据流

### 剪贴板文字 → 语音

```
ClipboardWatcher.text_changed
    → TextFilter（防抖、长度、去重）
    → mode == ask ? PromptBubble : SpeechService.speak()
    → split_sentences → chunks
    → _PipelineWorker（按块 TTS）
    → chunk_ready → AudioPlayer.enqueue（边下边播）
    → playback_finished → UI 恢复空闲
```

### 热键 → 语音

```
HotkeyService（pynput）
    → 模拟 Ctrl+C
    → 读取剪贴板文字
    → SpeechService.speak()（不走 ask/auto）
```

### 剪贴板图片 → OCR → 语音

```
ClipboardWatcher.image_changed
    → PromptBubble（询问）或 OcrService（自动）
    → OcrService（Vision API、JPEG 上传）
    → text_ready → SpeechService.speak()
```

## TTS 流水线

| 步骤 | 组件 | 说明 |
|------|------|------|
| 分句 | `split_sentences()` | 中英文句末标点 |
| 切块 | `make_chunks(n)` | `sentences_per_chunk` |
| 请求 | `_ChunkWorker` | `edge` → edge-tts；`openai` → httpx |
| 缓存 | SHA1 文件名 | 按 MB 淘汰 |
| 播放 | `AudioPlayer` | 单次朗读顺序队列 |

## 线程模型

- **主线程**：Qt UI、信号槽
- **热键线程**：`pynput` 监听
- **TTS 线程**：`QThread` + `_PipelineWorker`（顺序请求各块）
- **Edge TTS**：工作线程内 `asyncio.run`

## 配置生命周期

1. `Config()` 合并 `DEFAULT` 与 `config.json`
2. 设置对话框保存并写入 API Key
3. 保存后 `reload()`；热键变更则重启 `HotkeyService`

## 单实例（Windows）

`main.py` 中 `CreateMutexW` 在应用循环前执行。

## 外部依赖

| 包 | 作用 |
|----|------|
| PySide6 | GUI、剪贴板、媒体播放 |
| httpx | TTS + OCR HTTP |
| edge-tts | 微软神经 TTS |
| pynput | 全局热键、按键模拟 |
| keyring | API Key |
| platformdirs | 配置路径 |
| Pillow | OCR 图片编码 |

## 扩展点

- 新 TTS 后端：在 `_ChunkWorker._fetch()` 与设置 UI 增加分支
- 新触发源：向 `TextFilter.feed` 或 `SpeechService.speak` 注入文本
- 替换 OCR：修改 `OcrService` 提示词与请求体
