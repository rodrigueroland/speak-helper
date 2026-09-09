"""Global hotkey parsing, registration adapters, and Qt-safe dispatch."""

from __future__ import annotations

import ctypes
import logging
import string
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, Protocol

from PySide6.QtCore import (
    QAbstractNativeEventFilter,
    QByteArray,
    QCoreApplication,
    QObject,
    Qt,
    Signal,
    Slot,
)

from .config import Config

logger = logging.getLogger(__name__)

ACTION_READ = "read"
ACTION_STOP = "stop"
ACTION_PAUSE = "pause"
ACTION_REPLAY = "replay"

_MODIFIER_ALIASES = {
    "control": "ctrl",
    "ctl": "ctrl",
    "option": "alt",
    "command": "cmd",
    "super": "win",
}
_MODIFIER_ORDER = ("ctrl", "alt", "shift", "win", "cmd")


@dataclass(frozen=True, slots=True)
class ParsedHotkey:
    modifiers: tuple[str, ...]
    key: str

    @property
    def canonical(self) -> str:
        return "+".join((*self.modifiers, self.key))


@dataclass(frozen=True, slots=True)
class RegistrationResult:
    action: str
    hotkey: str
    registered: bool
    error_code: int = 0
    reason: str = ""


def parse_hotkey(combo: str) -> ParsedHotkey:
    """Parse and canonicalize a global hotkey."""
    raw_parts = [part.strip().lower() for part in combo.split("+") if part.strip()]
    parts = [_MODIFIER_ALIASES.get(part, part) for part in raw_parts]
    modifiers = tuple(name for name in _MODIFIER_ORDER if name in parts)
    keys = [part for part in parts if part not in _MODIFIER_ORDER]
    if len(keys) != 1 or len(set(parts)) != len(parts):
        raise ValueError(f"Invalid hotkey: {combo}")
    key = keys[0]
    valid_named = {
        "backspace",
        "delete",
        "down",
        "end",
        "enter",
        "escape",
        "home",
        "insert",
        "left",
        "pagedown",
        "pageup",
        "right",
        "space",
        "tab",
        "up",
    }
    valid_key = (
        (len(key) == 1 and key in string.ascii_lowercase + string.digits)
        or key in valid_named
        or (key.startswith("f") and key[1:].isdigit() and 1 <= int(key[1:]) <= 24)
    )
    if not modifiers or not valid_key:
        raise ValueError(f"Invalid hotkey: {combo}")
    return ParsedHotkey(modifiers, key)


def _pynput_hotkey(combo: str) -> str:
    parsed = parse_hotkey(combo)
    aliases = {"win": "cmd", "cmd": "cmd"}
    modifiers = [f"<{aliases.get(part, part)}>" for part in parsed.modifiers]
    key = f"<{parsed.key}>" if len(parsed.key) > 1 else parsed.key
    return "+".join((*modifiers, key))


class HotkeyRegistrar(Protocol):
    def register(
        self, hotkeys: Mapping[str, str], callback: Callable[[str], None]
    ) -> list[RegistrationResult]: ...

    def unregister_all(self) -> None: ...


if sys.platform == "win32":
    from ctypes import wintypes

    class _MSG(ctypes.Structure):
        _fields_ = (
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", wintypes.POINT),
        )


class WindowsNativeHotkeyRegistrar(QAbstractNativeEventFilter):
    """Register system hotkeys on Qt's Windows message-loop thread."""

    WM_HOTKEY = 0x0312
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000
    _MODIFIERS: ClassVar[Mapping[str, int]] = {
        "alt": MOD_ALT,
        "ctrl": MOD_CONTROL,
        "shift": MOD_SHIFT,
        "win": MOD_WIN,
        "cmd": MOD_WIN,
    }
    _NAMED_KEYS: ClassVar[Mapping[str, int]] = {
        "backspace": 0x08,
        "tab": 0x09,
        "enter": 0x0D,
        "escape": 0x1B,
        "space": 0x20,
        "pageup": 0x21,
        "pagedown": 0x22,
        "end": 0x23,
        "home": 0x24,
        "left": 0x25,
        "up": 0x26,
        "right": 0x27,
        "down": 0x28,
        "insert": 0x2D,
        "delete": 0x2E,
    }

    def __init__(self) -> None:
        super().__init__()
        if sys.platform != "win32":
            raise RuntimeError("The native Windows registrar is only available on Windows")
        self._user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._user32.RegisterHotKey.argtypes = (
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_uint,
            ctypes.c_uint,
        )
        self._user32.RegisterHotKey.restype = ctypes.c_bool
        self._user32.UnregisterHotKey.argtypes = (ctypes.c_void_p, ctypes.c_int)
        self._user32.UnregisterHotKey.restype = ctypes.c_bool
        self._actions_by_id: dict[int, str] = {}
        self._callback: Callable[[str], None] | None = None
        self._installed = False

    @classmethod
    def windows_codes(cls, combo: str) -> tuple[int, int]:
        parsed = parse_hotkey(combo)
        modifiers = cls.MOD_NOREPEAT
        for modifier in parsed.modifiers:
            modifiers |= cls._MODIFIERS[modifier]
        if len(parsed.key) == 1:
            virtual_key = ord(parsed.key.upper())
        elif parsed.key.startswith("f"):
            virtual_key = 0x70 + int(parsed.key[1:]) - 1
        else:
            virtual_key = cls._NAMED_KEYS[parsed.key]
        return modifiers, virtual_key

    def register(
        self, hotkeys: Mapping[str, str], callback: Callable[[str], None]
    ) -> list[RegistrationResult]:
        self.unregister_all()
        self._callback = callback
        application = QCoreApplication.instance()
        if application is None:
            raise RuntimeError("A Qt application is required before registering hotkeys")
        application.installNativeEventFilter(self)
        self._installed = True
        results: list[RegistrationResult] = []
        for identifier, (action, combo) in enumerate(hotkeys.items(), start=0x5200):
            try:
                modifiers, virtual_key = self.windows_codes(combo)
            except (KeyError, ValueError) as exc:
                results.append(RegistrationResult(action, combo, False, reason=str(exc)))
                continue
            ctypes.set_last_error(0)
            registered = bool(self._user32.RegisterHotKey(None, identifier, modifiers, virtual_key))
            error_code = ctypes.get_last_error() if not registered else 0
            if registered:
                self._actions_by_id[identifier] = action
            results.append(
                RegistrationResult(
                    action,
                    parse_hotkey(combo).canonical,
                    registered,
                    error_code=error_code,
                    reason="hotkey conflict" if not registered else "",
                )
            )
        return results

    def unregister_all(self) -> None:
        for identifier in tuple(self._actions_by_id):
            self._user32.UnregisterHotKey(None, identifier)
        self._actions_by_id.clear()
        if self._installed:
            application = QCoreApplication.instance()
            if application is not None:
                application.removeNativeEventFilter(self)
            self._installed = False

    def nativeEventFilter(
        self,
        event_type: QByteArray | bytes | bytearray | memoryview[int],
        message: int,
    ) -> tuple[bool, int]:
        del event_type
        if sys.platform != "win32":  # pragma: no cover
            return False, 0
        native_message = ctypes.cast(int(message), ctypes.POINTER(_MSG)).contents
        if native_message.message != self.WM_HOTKEY:
            return False, 0
        action = self._actions_by_id.get(int(native_message.wParam))
        if action and self._callback:
            self._callback(action)
            return True, 0
        return False, 0


class PynputHotkeyRegistrar:
    """Cross-platform fallback for systems without RegisterHotKey."""

    def __init__(self) -> None:
        self._listener: Any = None

    def register(
        self, hotkeys: Mapping[str, str], callback: Callable[[str], None]
    ) -> list[RegistrationResult]:
        self.unregister_all()
        try:
            from pynput import keyboard  # type: ignore[import-untyped]
        except ImportError as exc:
            return [
                RegistrationResult(action, combo, False, reason=str(exc))
                for action, combo in hotkeys.items()
            ]
        bindings: dict[str, Callable[[], None]] = {}
        results: list[RegistrationResult] = []
        for action, combo in hotkeys.items():
            try:

                def dispatch(selected: str = action) -> None:
                    callback(selected)

                bindings[_pynput_hotkey(combo)] = dispatch
                results.append(RegistrationResult(action, parse_hotkey(combo).canonical, True))
            except ValueError as exc:
                results.append(RegistrationResult(action, combo, False, reason=str(exc)))
        if bindings:
            self._listener = keyboard.GlobalHotKeys(bindings)
            self._listener.start()
        return results

    def unregister_all(self) -> None:
        listener = self._listener
        self._listener = None
        if listener is not None:
            listener.stop()


class HotkeyService(QObject):
    """Own hotkey lifecycle and deliver all actions on the Qt main thread."""

    read_requested = Signal()
    stop_requested = Signal()
    pause_requested = Signal()
    replay_requested = Signal()
    registration_changed = Signal(str, bool, str)
    error = Signal(str)
    _action_received = Signal(str)

    def __init__(
        self,
        config: Config,
        parent: QObject | None = None,
        registrar: HotkeyRegistrar | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._enabled = config.hotkey_enabled
        self._registrar = registrar or (
            WindowsNativeHotkeyRegistrar() if sys.platform == "win32" else PynputHotkeyRegistrar()
        )
        self._results: dict[str, RegistrationResult] = {}
        self._action_received.connect(self._dispatch, Qt.ConnectionType.QueuedConnection)

    @property
    def results(self) -> Mapping[str, RegistrationResult]:
        return dict(self._results)

    def start(self) -> None:
        self.stop()
        if not self._enabled:
            return
        hotkeys = {
            ACTION_READ: self._config.hotkey,
            ACTION_STOP: self._config.stop_hotkey,
            ACTION_PAUSE: self._config.pause_hotkey,
            ACTION_REPLAY: self._config.replay_hotkey,
        }
        canonical_values: set[str] = set()
        valid_hotkeys: dict[str, str] = {}
        for action, combo in hotkeys.items():
            try:
                canonical = parse_hotkey(combo).canonical
                if canonical in canonical_values:
                    result = RegistrationResult(action, combo, False, reason="duplicate hotkey")
                    self._report(result)
                    continue
                canonical_values.add(canonical)
                valid_hotkeys[action] = combo
            except ValueError as exc:
                self._report(RegistrationResult(action, combo, False, reason=str(exc)))
        try:
            for result in self._registrar.register(valid_hotkeys, self._action_received.emit):
                self._report(result)
        except Exception as exc:
            logger.exception("hotkey_registration_failed")
            self.error.emit(str(exc))

    def stop(self) -> None:
        self._registrar.unregister_all()
        self._results.clear()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled
        if enabled:
            self.start()
        else:
            self.stop()

    def _report(self, result: RegistrationResult) -> None:
        self._results[result.action] = result
        self.registration_changed.emit(result.action, result.registered, result.reason)
        if result.registered:
            logger.info("hotkey_registered action=%s hotkey=%s", result.action, result.hotkey)
        else:
            logger.error(
                "hotkey_registration_failed action=%s hotkey=%s code=%d reason=%s",
                result.action,
                result.hotkey,
                result.error_code,
                result.reason,
            )

    @Slot(str)
    def _dispatch(self, action: str) -> None:
        logger.info("hotkey_triggered action=%s", action)
        signals = {
            ACTION_READ: self.read_requested,
            ACTION_STOP: self.stop_requested,
            ACTION_PAUSE: self.pause_requested,
            ACTION_REPLAY: self.replay_requested,
        }
        signal = signals.get(action)
        if signal is not None:
            signal.emit()
