"""Selected-text capture transaction tests."""

from speak_helper.config import Config
from speak_helper.selection_capture import (
    ClipboardSnapshot,
    SelectionCaptureService,
    WindowsCopyInjector,
)


class FakeClipboard:
    def __init__(self, text: str = "before") -> None:
        self.sequence = 10
        self.current_text = text
        self.restored: ClipboardSnapshot | None = None
        self.text_failures = 0
        self.restore_fails = False

    def sequence_number(self) -> int:
        return self.sequence

    def snapshot(self) -> ClipboardSnapshot:
        return ClipboardSnapshot((("text/plain", self.current_text.encode()),))

    def text(self) -> str:
        if self.text_failures:
            self.text_failures -= 1
            raise RuntimeError("clipboard is temporarily locked")
        return self.current_text

    def restore(self, snapshot: ClipboardSnapshot) -> None:
        if self.restore_fails:
            raise RuntimeError("clipboard restore failed")
        self.restored = snapshot


class FakeInjector:
    def __init__(self, succeeds: bool = True) -> None:
        self.succeeds = succeeds
        self.calls = 0

    def copy(self) -> bool:
        self.calls += 1
        return self.succeeds


class RaisingInjector:
    def copy(self) -> bool:
        raise RuntimeError("input injection unavailable")


class RaisingSnapshotClipboard(FakeClipboard):
    def snapshot(self) -> ClipboardSnapshot:
        raise RuntimeError("clipboard unavailable")


class ModifierAwareInjector(FakeInjector):
    def __init__(self) -> None:
        super().__init__()
        self.released = False

    def modifiers_released(self) -> bool:
        return self.released


def test_windows_copy_injector_detects_held_modifiers() -> None:
    injector = WindowsCopyInjector.__new__(WindowsCopyInjector)
    states: dict[int, int] = {}
    injector._get_async_key_state = lambda key: states.get(key, 0)

    assert injector.modifiers_released()
    states[injector.VK_MENU] = -32768
    assert not injector.modifiers_released()


def test_capture_accepts_repeated_text_and_restores_clipboard(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    clipboard = FakeClipboard("same text")
    injector = FakeInjector()
    service = SelectionCaptureService(config, clipboard=clipboard, injector=injector)
    received: list[str] = []
    service.text_ready.connect(received.append)

    service.capture()
    qtbot.waitUntil(lambda: injector.calls == 1, timeout=1_000)
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

    assert signal.args == ["capture_failed"]


def test_capture_reports_injection_exception(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    service = SelectionCaptureService(config, clipboard=FakeClipboard(), injector=RaisingInjector())

    with qtbot.waitSignal(service.error, timeout=1_000) as signal:
        service.capture()

    assert signal.args == ["capture_failed"]


def test_capture_reports_snapshot_failure_without_starting(tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    service = SelectionCaptureService(
        config, clipboard=RaisingSnapshotClipboard(), injector=FakeInjector()
    )
    errors: list[str] = []
    service.error.connect(errors.append)

    service.capture()

    assert errors == ["capture_failed"]
    assert not service.active


def test_capture_timeout_restores_clipboard(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    clipboard = FakeClipboard()
    injector = FakeInjector()
    now = [0.0]
    service = SelectionCaptureService(
        config, clipboard=clipboard, injector=injector, clock=lambda: now[0]
    )
    errors: list[str] = []
    service.error.connect(errors.append)

    service.capture()
    qtbot.waitUntil(lambda: injector.calls == 1, timeout=1_000)
    now[0] = 2.0
    service._poll()
    qtbot.waitUntil(lambda: not service.active, timeout=1_000)

    assert errors == ["capture_timeout"]
    assert clipboard.restored is not None


def test_capture_retries_temporarily_unavailable_text(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    clipboard = FakeClipboard("delayed text")
    clipboard.text_failures = 1
    injector = FakeInjector()
    service = SelectionCaptureService(config, clipboard=clipboard, injector=injector)
    received: list[str] = []
    service.text_ready.connect(received.append)

    service.capture()
    qtbot.waitUntil(lambda: injector.calls == 1, timeout=1_000)
    clipboard.sequence += 1
    service._poll()
    assert service.active
    service._poll()
    qtbot.waitUntil(lambda: not service.active, timeout=1_000)

    assert received == ["delayed text"]


def test_restore_failure_is_reported_without_leaving_capture_active(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    clipboard = FakeClipboard("selected")
    clipboard.restore_fails = True
    injector = FakeInjector()
    service = SelectionCaptureService(config, clipboard=clipboard, injector=injector)
    errors: list[str] = []
    service.error.connect(errors.append)

    service.capture()
    qtbot.waitUntil(lambda: injector.calls == 1, timeout=1_000)
    clipboard.sequence += 1
    service._poll()
    qtbot.waitUntil(lambda: not service.active, timeout=1_000)

    assert errors == ["restore_failed"]


def test_capture_waits_for_physical_hotkey_release(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    injector = ModifierAwareInjector()
    service = SelectionCaptureService(config, clipboard=FakeClipboard(), injector=injector)

    service.capture()
    qtbot.wait(50)
    assert injector.calls == 0

    injector.released = True
    qtbot.waitUntil(lambda: injector.calls == 1, timeout=1_000)


def test_modifier_release_timeout_finishes_without_copy(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    injector = ModifierAwareInjector()
    now = [0.0]
    service = SelectionCaptureService(
        config,
        clipboard=FakeClipboard(),
        injector=injector,
        clock=lambda: now[0],
    )
    errors: list[str] = []
    service.error.connect(errors.append)

    service.capture()
    now[0] = 2.0
    service._wait_for_modifier_release()
    qtbot.waitUntil(lambda: not service.active, timeout=1_000)

    assert injector.calls == 0
    assert errors == ["modifier_release_timeout"]
