"""全局快捷键服务
流程：Ctrl+Alt+R → 保存剪贴板 → 模拟 Ctrl+C → 150ms 后读新内容 → 恢复 → 发出信号
"""
from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QGuiApplication

from .config import Config

try:
    from pynput import keyboard as _kb
    from pynput.keyboard import Controller as _KbCtrl
    from pynput.keyboard import Key as _Key
    _HAS_PYNPUT = True
except ImportError:
    _HAS_PYNPUT = False


def _parse_hotkey(combo: str) -> str:
    """'ctrl+alt+r' → '<ctrl>+<alt>+r'（pynput GlobalHotKeys 格式）"""
    _modifiers = {"ctrl", "alt", "shift", "cmd", "win", "super"}
    parts = combo.lower().split("+")
    return "+".join(f"<{p}>" if p in _modifiers else p for p in parts)


class HotkeyService(QObject):
    """监听全局热键；触发后捕获当前选中文字并发出 text_ready 信号"""

    text_ready = Signal(str)
    error = Signal(str)

    # 内部信号，用于从 pynput 线程安全跳回 Qt 主线程
    _triggered = Signal()

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._enabled = config.hotkey_enabled
        self._listener: "_kb.GlobalHotKeys | None" = None
        self._kb_ctrl = _KbCtrl() if _HAS_PYNPUT else None

        # QueuedConnection 保证槽函数在主线程执行
        self._triggered.connect(self._on_main_thread, Qt.ConnectionType.QueuedConnection)

    # ── public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        if not _HAS_PYNPUT:
            self.error.emit("pynput 未安装，全局快捷键不可用")
            return
        try:
            combo = _parse_hotkey(self._config.hotkey)
            self._listener = _kb.GlobalHotKeys({combo: self._on_hotkey_thread})
            self._listener.start()
        except Exception as exc:
            self.error.emit(f"快捷键注册失败：{exc}")

    def stop(self) -> None:
        if self._listener:
            self._listener.stop()
            self._listener = None

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    # ── private ───────────────────────────────────────────────────────────────

    def _on_hotkey_thread(self) -> None:
        """pynput 线程中执行，仅发射 Qt 信号（线程安全）"""
        if self._enabled:
            self._triggered.emit()

    def _on_main_thread(self) -> None:
        """Qt 主线程：保存剪贴板，后台模拟 Ctrl+C，定时读回"""
        clipboard = QGuiApplication.clipboard()
        saved_text = clipboard.text()

        def simulate_and_wait() -> None:
            time.sleep(0.08)   # 等热键按键完全松开
            if self._kb_ctrl:
                self._kb_ctrl.press(_Key.ctrl)
                self._kb_ctrl.press("c")
                self._kb_ctrl.release("c")
                self._kb_ctrl.release(_Key.ctrl)
            # 回主线程读取
            QTimer.singleShot(160, lambda: self._read_and_restore(saved_text))

        threading.Thread(target=simulate_and_wait, daemon=True).start()

    def _read_and_restore(self, saved_text: str) -> None:
        """在主线程中读剪贴板、恢复原内容、发出文本信号"""
        clipboard = QGuiApplication.clipboard()
        new_text = clipboard.text().strip()

        # 恢复原剪贴板（延迟 50ms，避免与读取竞争）
        if saved_text:
            QTimer.singleShot(50, lambda: clipboard.setText(saved_text))

        if new_text and new_text != saved_text.strip():
            self.text_ready.emit(new_text)
