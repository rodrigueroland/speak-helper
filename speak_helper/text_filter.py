"""Debounce, deduplicate, and bound clipboard text."""

from __future__ import annotations

import hashlib

from PySide6.QtCore import QObject, QTimer, Signal

from .config import Config


class TextFilter(QObject):
    """Emit accepted text after deduplication, debouncing, and length checks."""

    text_accepted = Signal(str)

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._last_hash = ""
        self._pending = ""

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._emit)

    def feed(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        if len(text) < self._config.min_length:
            return

        trimmed = text[: self._config.max_length]
        h = hashlib.md5(trimmed.encode("utf-8", errors="replace")).hexdigest()
        if h == self._last_hash:
            return

        self._last_hash = h
        self._pending = trimmed

        # Restart the debounce window for the newest clipboard event.
        self._timer.start(self._config.debounce_ms)

    def reset_dedup(self) -> None:
        """Allow the same text to be accepted by the next event."""
        self._last_hash = ""

    def _emit(self) -> None:
        if self._pending:
            self.text_accepted.emit(self._pending)
