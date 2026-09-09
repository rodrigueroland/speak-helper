"""Reliable selected-text capture with clipboard restoration."""

from __future__ import annotations

import ctypes
import logging
import sys
import time
from collections.abc import Callable
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any, Protocol

from PySide6.QtCore import QMimeData, QObject, QTimer, Signal
from PySide6.QtGui import QClipboard, QGuiApplication

from .config import Config

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ClipboardSnapshot:
    formats: tuple[tuple[str, bytes], ...]


class ClipboardAdapter(Protocol):
    def sequence_number(self) -> int: ...

    def snapshot(self) -> ClipboardSnapshot: ...

    def text(self) -> str: ...

    def restore(self, snapshot: ClipboardSnapshot) -> None: ...


class CopyInjector(Protocol):
    def copy(self) -> bool: ...


class QtClipboardAdapter:
    """Qt clipboard access plus the native Windows change sequence."""

    def __init__(self, clipboard: QClipboard | None = None) -> None:
        selected = clipboard or QGuiApplication.clipboard()
        if selected is None:
            raise RuntimeError("The system clipboard is unavailable")
        self._clipboard = selected
        self._revision = 0
        self._clipboard.dataChanged.connect(self._increment_revision)
        if sys.platform == "win32":
            self._get_sequence: Callable[[], int] = ctypes.windll.user32.GetClipboardSequenceNumber
        else:
            self._get_sequence = lambda: self._revision

    def _increment_revision(self) -> None:
        self._revision += 1

    def sequence_number(self) -> int:
        return int(self._get_sequence())

    def snapshot(self) -> ClipboardSnapshot:
        mime = self._clipboard.mimeData()
        if mime is None:
            return ClipboardSnapshot(())
        formats = tuple((name, bytes(mime.data(name).data())) for name in mime.formats())
        return ClipboardSnapshot(formats)

    def text(self) -> str:
        mime = self._clipboard.mimeData()
        return mime.text() if mime is not None and mime.hasText() else ""

    def restore(self, snapshot: ClipboardSnapshot) -> None:
        if not snapshot.formats:
            self._clipboard.clear()
            return
        mime = QMimeData()
        for name, value in snapshot.formats:
            mime.setData(name, value)
        self._clipboard.setMimeData(mime)


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = (
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    )


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = (
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", wintypes.WPARAM),
    )


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = (
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    )


class _INPUTUNION(ctypes.Union):
    _fields_ = (("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT), ("hi", _HARDWAREINPUT))


class _INPUT(ctypes.Structure):
    _anonymous_ = ("union",)
    _fields_ = (("type", wintypes.DWORD), ("union", _INPUTUNION))


class WindowsCopyInjector:
    """Inject Ctrl+C as one uninterrupted SendInput batch."""

    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    VK_CONTROL = 0x11
    VK_C = 0x43
    _send_input: Any

    def __init__(self) -> None:
        if sys.platform != "win32":
            raise RuntimeError("Windows input injection is only available on Windows")
        self._send_input = ctypes.windll.user32.SendInput
        self._send_input.argtypes = (ctypes.c_uint, ctypes.POINTER(_INPUT), ctypes.c_int)
        self._send_input.restype = ctypes.c_uint

    def copy(self) -> bool:
        inputs = (_INPUT * 4)(
            _INPUT(type=self.INPUT_KEYBOARD, ki=_KEYBDINPUT(wVk=self.VK_CONTROL)),
            _INPUT(type=self.INPUT_KEYBOARD, ki=_KEYBDINPUT(wVk=self.VK_C)),
            _INPUT(
                type=self.INPUT_KEYBOARD,
                ki=_KEYBDINPUT(wVk=self.VK_C, dwFlags=self.KEYEVENTF_KEYUP),
            ),
            _INPUT(
                type=self.INPUT_KEYBOARD,
                ki=_KEYBDINPUT(wVk=self.VK_CONTROL, dwFlags=self.KEYEVENTF_KEYUP),
            ),
        )
        return self._send_input(len(inputs), inputs, ctypes.sizeof(_INPUT)) == len(inputs)


class PynputCopyInjector:
    """Cross-platform selection-copy fallback."""

    def copy(self) -> bool:
        try:
            from pynput.keyboard import Controller, Key  # type: ignore[import-untyped]

            controller = Controller()
            modifier = Key.cmd if sys.platform == "darwin" else Key.ctrl
            with controller.pressed(modifier):
                controller.press("c")
                controller.release("c")
            return True
        except Exception:
            logger.exception("copy_injection_failed")
            return False


class SelectionCaptureService(QObject):
    """Coordinate copy, clipboard change detection, capture, and restoration."""

    capture_started = Signal()
    clipboard_changed = Signal()
    text_ready = Signal(str)
    error = Signal(str)
    capture_finished = Signal()

    def __init__(
        self,
        config: Config,
        parent: QObject | None = None,
        clipboard: ClipboardAdapter | None = None,
        injector: CopyInjector | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._clipboard = clipboard or QtClipboardAdapter()
        self._injector = injector or (
            WindowsCopyInjector() if sys.platform == "win32" else PynputCopyInjector()
        )
        self._clock = clock
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._poll)
        self._active = False
        self._change_seen = False
        self._initial_sequence = 0
        self._started_at = 0.0
        self._snapshot = ClipboardSnapshot(())

    @property
    def active(self) -> bool:
        return self._active

    def capture(self) -> None:
        if self._active:
            self.error.emit("capture_busy")
            return
        self._active = True
        self._change_seen = False
        self._snapshot = self._clipboard.snapshot()
        self._initial_sequence = self._clipboard.sequence_number()
        self._started_at = self._clock()
        logger.info("selection_capture_started sequence=%d", self._initial_sequence)
        self.capture_started.emit()
        # Let the global-hotkey keys return to their physical state before Ctrl+C.
        QTimer.singleShot(75, self._send_copy)

    def cancel(self) -> None:
        if self._active:
            self._restore_and_finish()

    def _send_copy(self) -> None:
        if not self._active:
            return
        if not self._injector.copy():
            self.error.emit("capture_failed")
            self._restore_and_finish()
            return
        self._poll_timer.start(self._config.clipboard_poll_interval_ms)

    def _poll(self) -> None:
        if not self._active:
            self._poll_timer.stop()
            return
        if self._clipboard.sequence_number() != self._initial_sequence:
            if not self._change_seen:
                self._change_seen = True
                logger.info("clipboard_changed")
                self.clipboard_changed.emit()
            text = self._clipboard.text().strip()
            if text:
                logger.info("text_captured length=%d", len(text))
                self.text_ready.emit(text)
                self._restore_and_finish()
                return
        elapsed_ms = (self._clock() - self._started_at) * 1_000
        if elapsed_ms >= self._config.capture_timeout_ms:
            logger.warning("selection_capture_timeout elapsed_ms=%d", int(elapsed_ms))
            self.error.emit("capture_timeout")
            self._restore_and_finish()

    def _restore_and_finish(self) -> None:
        self._poll_timer.stop()
        if self._config.restore_clipboard:
            self._clipboard.restore(self._snapshot)
            QTimer.singleShot(75, self._finish)
        else:
            self._finish()

    def _finish(self) -> None:
        if not self._active:
            return
        self._active = False
        self.capture_finished.emit()
