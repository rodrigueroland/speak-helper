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


def _press_probe_hotkey() -> None:
    from speak_helper.selection_capture import _INPUT, _KEYBDINPUT

    input_keyboard = 1
    key_up = 0x0002
    keys = (0x11, 0x12, 0x10, 0x87)  # Control, Alt, Shift, F24
    events = [_INPUT(type=input_keyboard, ki=_KEYBDINPUT(wVk=key)) for key in keys] + [
        _INPUT(type=input_keyboard, ki=_KEYBDINPUT(wVk=key, dwFlags=key_up))
        for key in reversed(keys)
    ]
    batch = (_INPUT * len(events))(*events)
    sent = ctypes.windll.user32.SendInput(len(batch), batch, ctypes.sizeof(_INPUT))
    if sent != len(batch):
        raise RuntimeError(f"SendInput inserted {sent} of {len(batch)} events")


def main() -> int:
    if sys.platform != "win32":
        print("This integration probe requires Windows.")
        return 2

    application = QApplication(sys.argv)
    editor = QPlainTextEdit()
    editor.setWindowTitle("Speak Helper selection probe")
    editor.resize(600, 180)
    expected = [f"Selection probe {index}: français — Unicode ✓" for index in range(ITERATIONS)]
    captured: list[str] = []
    exit_code = 1

    with tempfile.TemporaryDirectory(prefix="speak-helper-probe-") as temporary:
        config = Config(config_dir=Path(temporary), locale_name="en_US")
        config.set("trigger", "hotkey", "ctrl+alt+shift+f24")
        config.set("trigger", "stop_hotkey", "ctrl+alt+shift+f21")
        config.set("trigger", "pause_hotkey", "ctrl+alt+shift+f22")
        config.set("trigger", "replay_hotkey", "ctrl+alt+shift+f23")
        capture = SelectionCaptureService(config)
        hotkeys = HotkeyService(config)
        hotkeys.read_requested.connect(capture.capture)

        def select_iteration(index: int) -> None:
            editor.setPlainText(expected[index])
            editor.selectAll()
            editor.setFocus()
            editor.activateWindow()
            editor.raise_()
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

    print(f"Captured {len(captured)}/{ITERATIONS} selections correctly.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
