"""Exercise the native hotkey-to-selected-text path repeatedly on Windows."""

from __future__ import annotations

import ctypes
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from speak_helper.config import Config
from speak_helper.hotkey_service import ACTION_READ, HotkeyService
from speak_helper.selection_capture import SelectionCaptureService

ITERATIONS = 10
_PROBE_KEYS = (0x11, 0x12, 0x10, 0x87)  # Control, Alt, Shift, F24


def _send_probe_keys(keys: tuple[int, ...], *, release: bool = False) -> None:
    from speak_helper.selection_capture import _INPUT, _KEYBDINPUT

    input_keyboard = 1
    key_up = 0x0002
    events = [
        _INPUT(
            type=input_keyboard,
            ki=_KEYBDINPUT(wVk=key, dwFlags=key_up if release else 0),
        )
        for key in keys
    ]
    batch = (_INPUT * len(events))(*events)
    sent = ctypes.windll.user32.SendInput(len(batch), batch, ctypes.sizeof(_INPUT))
    if sent != len(batch):
        raise RuntimeError(f"SendInput inserted {sent} of {len(batch)} events")


def _press_probe_hotkey() -> None:
    _send_probe_keys(_PROBE_KEYS)
    # Hold the chord long enough to exercise native modifier-release detection.
    QTimer.singleShot(80, lambda: _send_probe_keys(tuple(reversed(_PROBE_KEYS)), release=True))


def main() -> int:
    if sys.platform != "win32":
        print("This integration probe requires Windows.")
        return 2

    application = QApplication(sys.argv)
    capture_only = "--capture-only" in sys.argv
    editor = QPlainTextEdit()
    editor.setWindowTitle("Speak Helper selection probe")
    editor.resize(600, 180)
    expected = [f"Selection probe {index}: français — Unicode ✓" for index in range(ITERATIONS)]
    captured: list[str] = []
    hotkey_triggers = 0
    capture_starts = 0
    exit_code = 1

    with tempfile.TemporaryDirectory(prefix="speak-helper-probe-") as temporary:
        config = Config(config_dir=Path(temporary), locale_name="en_US")
        config.set("trigger", "hotkey", "ctrl+alt+shift+f24")
        config.set("trigger", "stop_hotkey", "ctrl+alt+shift+f21")
        config.set("trigger", "pause_hotkey", "ctrl+alt+shift+f22")
        config.set("trigger", "replay_hotkey", "ctrl+alt+shift+f23")
        capture = SelectionCaptureService(config)
        hotkeys = HotkeyService(config)

        def on_hotkey() -> None:
            nonlocal hotkey_triggers
            hotkey_triggers += 1
            capture.capture()

        def on_capture_started() -> None:
            nonlocal capture_starts
            capture_starts += 1

        hotkeys.read_requested.connect(on_hotkey)
        capture.capture_started.connect(on_capture_started)

        def select_iteration(index: int) -> None:
            editor.setPlainText(expected[index])
            editor.selectAll()
            editor.setFocus()
            editor.activateWindow()
            editor.raise_()
            if capture_only:
                QTimer.singleShot(120, lambda: _send_probe_keys(_PROBE_KEYS[:-1]))
                QTimer.singleShot(140, capture.capture)
                QTimer.singleShot(
                    220,
                    lambda: _send_probe_keys(tuple(reversed(_PROBE_KEYS[:-1])), release=True),
                )
            else:
                QTimer.singleShot(120, _press_probe_hotkey)

        def on_text(text: str) -> None:
            captured.append(text)

        def on_finished() -> None:
            nonlocal exit_code
            if len(captured) < ITERATIONS:
                QTimer.singleShot(120, lambda: select_iteration(len(captured)))
                return
            exit_code = 0 if captured == expected else 1
            QTimer.singleShot(0, application.quit)

        def on_error(reason: str) -> None:
            print(f"Capture failed: {reason}")
            application.quit()

        capture.text_ready.connect(on_text)
        capture.capture_finished.connect(on_finished)
        capture.error.connect(on_error)
        hotkeys.start()
        result = hotkeys.results.get(ACTION_READ)
        if result is None or not result.registered:
            print(f"Probe hotkey registration failed: {result}")
            return 1

        editor.show()
        QTimer.singleShot(400, lambda: select_iteration(0))
        QTimer.singleShot(20_000, application.quit)
        application.exec()
        capture.cancel()
        hotkeys.stop()

    print(
        f"Mode {'capture-only' if capture_only else 'hotkey'}; hotkeys "
        f"{hotkey_triggers}/{ITERATIONS}; captures started "
        f"{capture_starts}/{ITERATIONS}; text captured {len(captured)}/{ITERATIONS}."
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
