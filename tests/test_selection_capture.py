"""Selected-text capture transaction tests."""

from speak_helper.config import Config
from speak_helper.selection_capture import ClipboardSnapshot, SelectionCaptureService


class FakeClipboard:
    def __init__(self, text: str = "before") -> None:
        self.sequence = 10
        self.current_text = text
        self.restored: ClipboardSnapshot | None = None

    def sequence_number(self) -> int:
        return self.sequence

    def snapshot(self) -> ClipboardSnapshot:
        return ClipboardSnapshot((("text/plain", self.current_text.encode()),))

    def text(self) -> str:
        return self.current_text

    def restore(self, snapshot: ClipboardSnapshot) -> None:
        self.restored = snapshot


class FakeInjector:
    def __init__(self, succeeds: bool = True) -> None:
        self.succeeds = succeeds
        self.calls = 0

    def copy(self) -> bool:
        self.calls += 1
        return self.succeeds


def test_capture_accepts_repeated_text_and_restores_clipboard(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    clipboard = FakeClipboard("same text")
    injector = FakeInjector()
    service = SelectionCaptureService(config, clipboard=clipboard, injector=injector)
    received: list[str] = []
    service.text_ready.connect(received.append)

    service.capture()
    service._send_copy()
    clipboard.sequence += 1
    service._poll()
    qtbot.waitUntil(lambda: not service.active, timeout=1_000)

    assert received == ["same text"]
    assert clipboard.restored is not None
    assert injector.calls == 1


def test_capture_reports_injection_failure(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    service = SelectionCaptureService(
        config, clipboard=FakeClipboard(), injector=FakeInjector(False)
    )

    with qtbot.waitSignal(service.error, timeout=1_000) as signal:
        service.capture()
        service._send_copy()

    assert signal.args == ["capture_failed"]


def test_capture_timeout_restores_clipboard(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    clipboard = FakeClipboard()
    now = [0.0]
    service = SelectionCaptureService(
        config, clipboard=clipboard, injector=FakeInjector(), clock=lambda: now[0]
    )
    errors: list[str] = []
    service.error.connect(errors.append)

    service.capture()
    service._send_copy()
    now[0] = 2.0
    service._poll()
    qtbot.waitUntil(lambda: not service.active, timeout=1_000)

    assert errors == ["capture_timeout"]
    assert clipboard.restored is not None
