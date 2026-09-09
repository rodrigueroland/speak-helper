"""Observe user-originated clipboard text and images."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication, QImage

from .config import Config


class ClipboardWatcher(QObject):
    text_changed = Signal(str)
    image_changed = Signal(QImage)

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._enabled = config.clipboard_enabled
        self._suppressed = False

        clipboard = QGuiApplication.clipboard()
        clipboard.dataChanged.connect(self._on_clipboard_changed)

    # ── public API ────────────────────────────────────────────────────────────

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def set_suppressed(self, suppressed: bool) -> None:
        """Ignore changes made by the selected-text capture transaction."""
        self._suppressed = suppressed

    @property
    def active(self) -> bool:
        return self._enabled and not self._suppressed

    # ── private ───────────────────────────────────────────────────────────────

    @staticmethod
    def _is_url(text: str) -> bool:
        """Return whether text contains only a URL."""
        t = text.strip()
        return t.startswith(("http://", "https://", "ftp://")) and " " not in t

    def _on_clipboard_changed(self) -> None:
        if not self.active:
            return
        clipboard = QGuiApplication.clipboard()
        mime = clipboard.mimeData()
        if mime is None:
            return

        # Ignore copied local files.
        if mime.hasUrls():
            urls = mime.urls()
            if urls and all(u.isLocalFile() for u in urls):
                return

        # Browsers may expose an image together with its source URL.
        if mime.hasImage() and mime.hasText() and self._is_url(mime.text()):
            img: QImage = clipboard.image()
            if not img.isNull():
                self.image_changed.emit(img)
            return

        # Normal text.
        if mime.hasText():
            text = mime.text().strip()
            if text:
                self.text_changed.emit(text)
            return

        # Image-only clipboard content.
        if mime.hasImage():
            image: QImage = clipboard.image()
            if not image.isNull():
                self.image_changed.emit(image)
