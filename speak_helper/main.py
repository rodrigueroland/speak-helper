"""应用主控制器：装配所有模块并连接信号"""
from __future__ import annotations

import sys

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication, QMessageBox

# ── 单例互斥锁（Windows Named Mutex） ─────────────────────────────────────────
_MUTEX_NAME = "Global\\SpeakHelper_SingleInstance_Mutex"
_mutex_handle = None   # 持有引用，防止 GC 释放导致锁丢失


def _acquire_single_instance() -> bool:
    """
    尝试创建全局命名 Mutex。
    返回 True 表示本进程是第一个实例；False 表示已有实例在运行。
    非 Windows 平台直接返回 True（放行）。
    """
    global _mutex_handle
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
        if handle and kernel32.GetLastError() == 183:   # ERROR_ALREADY_EXISTS
            kernel32.CloseHandle(handle)
            return False
        _mutex_handle = handle
        return True
    except Exception:
        return True   # 获取失败时放行，避免阻塞启动


from .audio_player import AudioPlayer
from .clipboard_watcher import ClipboardWatcher
from .config import Config
from .hotkey_service import HotkeyService
from .ocr_service import OcrService
from .speech_service import SpeechService
from .text_filter import TextFilter
from .ui.floating_dock import FloatingDock
from .ui.prompt_bubble import PromptBubble
from .ui.settings_dialog import SettingsDialog
from .ui.tray_icon import TrayIcon


class SpeakHelperApp:
    def __init__(self, app: QApplication) -> None:
        self._app = app
        self._last_text: str = ""
        self._paused = False
        self._pending_image = None   # 等待 OCR 的剪贴板图片

        # ── 初始化各模块 ──────────────────────────────────────────────────────
        self._config = Config()
        self._speech = SpeechService(self._config)
        self._player = AudioPlayer()
        self._text_filter = TextFilter(self._config)
        self._clip_watcher = ClipboardWatcher(self._config)
        self._hotkey = HotkeyService(self._config)
        self._ocr = OcrService(self._config)

        # ── UI ────────────────────────────────────────────────────────────────
        self._dock = FloatingDock(self._config)
        self._bubble = PromptBubble(self._config)
        self._tray = TrayIcon(self._config)

        self._settings_dlg: SettingsDialog | None = None

        self._connect_signals()
        self._hotkey.start()

    # ── signal wiring ─────────────────────────────────────────────────────────

    def _connect_signals(self) -> None:
        # 剪贴板文本 → 过滤 → 气泡或直接朗读
        self._clip_watcher.text_changed.connect(self._text_filter.feed)
        self._text_filter.text_accepted.connect(self._on_text_from_clipboard)

        # 剪贴板图片 → 先弹询问气泡 → 确认后 OCR → 语音
        self._clip_watcher.image_changed.connect(self._on_image_from_clipboard)
        self._bubble.image_confirmed.connect(self._start_ocr)
        self._ocr.text_ready.connect(self._speak)
        self._ocr.started.connect(lambda: self._dock.set_state("speaking"))
        self._ocr.started.connect(lambda: self._tray.show_message("OCR", "正在识别图片文字…"))
        self._ocr.error.connect(lambda msg: self._tray.show_message("OCR 失败", msg))
        self._ocr.error.connect(lambda _msg: self._dock.set_state("error"))

        # 快捷键 → 直接朗读（不走模式判断）
        self._hotkey.text_ready.connect(self._speak)
        self._hotkey.error.connect(lambda msg: self._tray.show_message("快捷键", msg))

        # 气泡确认 → 朗读
        self._bubble.confirmed.connect(self._speak)

        # TTS 分块就绪 → 入播放队列（边下边播）
        self._speech.chunk_ready.connect(
            lambda path, idx, total: self._player.enqueue(path, idx, total)
        )

        # 状态同步到 Dock 和 Tray
        self._speech.started.connect(self._player.reset)
        self._speech.started.connect(lambda: self._dock.set_state("speaking"))
        self._speech.started.connect(lambda: self._tray.set_state("speaking"))
        self._speech.finished.connect(lambda: self._dock.set_state("idle"))
        self._speech.finished.connect(lambda: self._tray.set_state("idle"))
        self._speech.error.connect(self._on_speech_error)
        self._player.playback_finished.connect(lambda: self._dock.set_state("idle"))
        self._player.playback_finished.connect(lambda: self._tray.set_state("idle"))
        self._player.playback_finished.connect(self._speech.finished.emit)
        self._player.error.connect(self._on_speech_error)

        # Dock 点击：暂停/继续；右键：显示托盘菜单
        self._dock.clicked.connect(self._on_dock_click)
        self._dock.double_clicked.connect(self._replay_last)
        self._dock.right_clicked.connect(self._show_dock_menu)

        # Tray 菜单
        self._tray.pause_toggled.connect(self._on_pause_toggle)
        self._tray.stop_requested.connect(self._stop)
        self._tray.replay_requested.connect(self._replay_last)
        self._tray.mode_changed.connect(self._on_mode_changed)
        self._tray.clipboard_toggled.connect(self._clip_watcher.set_enabled)
        self._tray.clipboard_toggled.connect(
            lambda en: self._config.set("trigger", "clipboard_enabled", en)
        )
        self._tray.hotkey_toggled.connect(self._hotkey.set_enabled)
        self._tray.hotkey_toggled.connect(
            lambda en: self._config.set("trigger", "hotkey_enabled", en)
        )
        self._tray.settings_requested.connect(self._show_settings)
        self._tray.about_requested.connect(self._show_about)
        self._tray.quit_requested.connect(self._quit)

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_text_from_clipboard(self, text: str) -> None:
        if self._paused:
            return
        if self._config.mode == "ask":
            self._bubble.show_for_text(text, self._dock)
        else:
            self._speak(text)

    def _on_image_from_clipboard(self, image) -> None:
        """剪贴板出现图片：存储后按模式决定直接 OCR 还是先询问。"""
        if self._paused:
            return
        self._pending_image = image
        if self._config.mode == "ask":
            self._bubble.show_for_image(self._dock)
        else:
            self._start_ocr()

    def _start_ocr(self) -> None:
        """气泡确认或自动模式下，对 pending image 执行 OCR。"""
        if self._pending_image is None:
            return
        self._ocr.recognize_clipboard_image(self._pending_image)
        self._pending_image = None

    def _speak(self, text: str) -> None:
        if not text.strip():
            return
        if self._config.backend == "openai" and not self._config.api_key:
            self._tray.show_message("Speak Helper", "请先在设置中填写 API Key")
            self._show_settings()
            return
        self._last_text = text
        self._text_filter.reset_dedup()   # 允许重读相同文本
        self._speech.speak(text)

    def _stop(self) -> None:
        self._speech.stop()
        self._player.stop()

    def _replay_last(self) -> None:
        if self._last_text:
            self._speak(self._last_text)

    def _on_dock_click(self) -> None:
        self._on_pause_toggle(not self._paused)

    def _show_dock_menu(self, pos: QPoint) -> None:
        self._tray._menu.exec(pos)

    def _on_pause_toggle(self, paused: bool) -> None:
        self._paused = paused
        state = "paused" if paused else "idle"
        self._dock.set_state(state)
        self._tray.set_state(state)
        self._clip_watcher.set_enabled(not paused and self._config.clipboard_enabled)
        self._hotkey.set_enabled(not paused and self._config.hotkey_enabled)

    def _on_mode_changed(self, mode: str) -> None:
        self._config.set("trigger", "mode", mode)
        self._config.save()

    def _on_speech_error(self, msg: str) -> None:
        self._dock.set_state("error")
        self._tray.set_state("error", msg)
        self._tray.show_message("朗读失败", msg)

    def _show_settings(self) -> None:
        if self._settings_dlg is None:
            self._settings_dlg = SettingsDialog(self._config)
            self._settings_dlg.saved.connect(self._on_settings_saved)
            self._settings_dlg.finished.connect(lambda _: setattr(self, "_settings_dlg", None))
        self._settings_dlg.show()
        self._settings_dlg.raise_()
        self._settings_dlg.activateWindow()

    def _on_settings_saved(self) -> None:
        # 从磁盘刷新内存配置，确保新值立即生效
        self._config.reload()
        # 重启快捷键（组合键可能已改变）
        self._hotkey.stop()
        self._hotkey.start()
        self._tray.show_message("设置已保存", "配置已生效")

    def _show_about(self) -> None:
        QMessageBox.about(
            None,
            "关于 Speak Helper",
            "<b>Speak Helper v0.0.1</b><br>"
            "选中文字，一键朗读。<br><br>"
            "使用 OpenAI 兼容 TTS API 进行语音合成。<br>"
            "支持 Windows / macOS / Linux。",
        )

    def _quit(self) -> None:
        self._hotkey.stop()
        self._player.stop()
        self._config.save()
        self._app.quit()


# ── 入口 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    # ── 单例检查（必须在 QApplication 之前，弹窗需要先建 app） ─────────────────
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Speak Helper")
    app.setApplicationVersion("0.0.1")

    if not _acquire_single_instance():
        QMessageBox.warning(
            None,
            "Speak Helper",
            "Speak Helper 已经在运行中。\n\n请检查系统托盘图标。",
        )
        sys.exit(0)

    controller = SpeakHelperApp(app)       # noqa: F841 — 必须持有引用

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
