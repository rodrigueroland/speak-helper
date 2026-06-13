# 安装

[English](../installation.md) · [中文](installation.md)

安装 Speak Helper — 跨平台桌面 **文字转语音 / 朗读** 工具，支持 Windows、macOS、Linux。

## 环境要求

| 项目 | 版本 |
|------|------|
| Python | 3.11+（推荐 3.13） |
| 显示环境 | 需要（PySide6 图形界面） |
| 音频 | 系统扬声器输出 |

打包可选：[uv](https://docs.astral.sh/uv/)、PyInstaller（dev 依赖）。

## 使用 uv 安装（推荐）

```powershell
cd speak_helper
uv venv
uv sync
uv run python -m speak_helper
```

开发依赖：

```powershell
uv sync --all-extras
```

## 使用 pip 安装

```bash
cd speak_helper
pip install -r requirements.txt
python -m speak_helper
```

可编辑安装（命令 `speak-helper`）：

```bash
pip install -e ".[dev]"
speak-helper
```

## Windows 说明

- **杀毒软件**：`pynput` 全局热键可能告警，将 Python 或 `SpeakHelper.exe` 加入白名单。
- **单实例**：重复启动会提示已在运行，请查看系统托盘。
- **配置目录**：`%APPDATA%\speak_helper\`。

## macOS 说明

- 热键失效时在 **系统设置 → 隐私与安全性 → 辅助功能** 中授权。
- 打包：`bash scripts/build_mac.sh` → `dist/SpeakHelper.app`。

## Linux 说明

- 播放失败时安装 Qt 多媒体依赖（如 `libqt6multimedia`）。
- Wayland 下全局热键可能需要额外权限。

## 打包可执行文件

### Windows

```powershell
.\scripts\build_win.ps1
```

产物：`dist\SpeakHelper\SpeakHelper.exe`、`dist\SpeakHelper-win64.zip`。

### macOS

```bash
bash scripts/build_mac.sh
```

产物：`dist/SpeakHelper.app`。

## 验证安装

```bash
uv run pytest tests/ -q
```

## 卸载

- 删除项目目录。
- 删除用户配置目录下的 `speak_helper`（缓存与 `config.json`）。
- 从凭据管理器 / Keychain 移除服务名 `speak_helper` 的 API Key。
