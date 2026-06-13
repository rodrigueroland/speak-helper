"""剪贴板监听：当剪贴板内容变化时发出信号（文本 or 图片）"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication, QImage

from .config import Config


class ClipboardWatcher(QObject):
    text_changed = Signal(str)
    image_changed = Signal(QImage)   # 剪贴板变为图片时触发

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._enabled = config.clipboard_enabled

        clipboard = QGuiApplication.clipboard()
        clipboard.dataChanged.connect(self._on_clipboard_changed)

    # ── public API ────────────────────────────────────────────────────────────

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _is_url(text: str) -> bool:
        """判断字符串是否是纯 URL（浏览器复制图片时会把来源 URL 写入文本）。"""
        t = text.strip()
        return t.startswith(("http://", "https://", "ftp://")) and " " not in t

    def _on_clipboard_changed(self) -> None:
        if not self._enabled:
            return
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        if mime is None:
            return

        # 复制本地文件时（全部是 file:// 路径）直接跳过
        if mime.hasUrls():
            urls = mime.urls()
            if urls and all(u.isLocalFile() for u in urls):
                return

        # 若剪贴板同时有图片和 URL 文本（浏览器"复制图片"场景），走图片路径
        if mime.hasImage() and mime.hasText() and self._is_url(mime.text()):
            img: QImage = clipboard.image()
            if not img.isNull():
                self.image_changed.emit(img)
            return

        # 普通文本
        if mime.hasText():
            text = mime.text().strip()
            if text:
                self.text_changed.emit(text)
            return

        # 纯图片（截图、图片编辑器复制等，无文本）
        if mime.hasImage():
            img: QImage = clipboard.image()
            if not img.isNull():
                self.image_changed.emit(img)
