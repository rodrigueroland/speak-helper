"""Hotkey parser, registration, conflicts, and cleanup."""

from collections.abc import Callable, Mapping

import pytest

from speak_helper.config import Config
from speak_helper.hotkey_service import (
    ACTION_READ,
    HotkeyService,
    RegistrationResult,
    parse_hotkey,
)


class FakeRegistrar:
    def __init__(self) -> None:
        self.registered: dict[str, str] = {}
        self.callback: Callable[[str], None] | None = None
        self.unregister_count = 0

    def register(
        self, hotkeys: Mapping[str, str], callback: Callable[[str], None]
    ) -> list[RegistrationResult]:
        self.registered = dict(hotkeys)
        self.callback = callback
        return [RegistrationResult(action, combo, True) for action, combo in hotkeys.items()]

    def unregister_all(self) -> None:
        self.unregister_count += 1
        self.registered.clear()


@pytest.mark.parametrize(
    ("source", "canonical"),
    [("Ctrl+Alt+R", "ctrl+alt+r"), ("shift+control+F8", "ctrl+shift+f8")],
)
def test_parse_hotkey(source: str, canonical: str) -> None:
    assert parse_hotkey(source).canonical == canonical


@pytest.mark.parametrize("source", ["r", "ctrl+alt", "ctrl+ctrl+r", "ctrl+💥"])
def test_parse_hotkey_rejects_invalid_values(source: str) -> None:
    with pytest.raises(ValueError):
        parse_hotkey(source)


def test_service_registers_dispatches_and_cleans_up(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    registrar = FakeRegistrar()
    service = HotkeyService(config, registrar=registrar)

    with qtbot.waitSignals([service.registration_changed] * 4, timeout=1_000):
        service.start()
    with qtbot.waitSignal(service.read_requested, timeout=1_000):
        assert registrar.callback is not None
        registrar.callback(ACTION_READ)
    service.stop()

    assert registrar.unregister_count == 2
    assert service.results == {}


def test_duplicate_hotkey_is_not_registered(tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    config.set("trigger", "stop_hotkey", config.hotkey)
    registrar = FakeRegistrar()
    service = HotkeyService(config, registrar=registrar)
    service.start()

    assert "stop" not in registrar.registered
    assert not service.results["stop"].registered


def test_hotkey_diagnostic_consumes_one_press(qtbot, tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    registrar = FakeRegistrar()
    service = HotkeyService(config, registrar=registrar)
    service.start()

    assert service.arm_test(ACTION_READ)
    with qtbot.waitSignal(service.test_triggered, timeout=1_000) as tested:
        assert registrar.callback is not None
        registrar.callback(ACTION_READ)
    assert tested.args == [ACTION_READ]

    with qtbot.waitSignal(service.read_requested, timeout=1_000):
        registrar.callback(ACTION_READ)


def test_hotkey_diagnostic_rejects_unregistered_action(tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    service = HotkeyService(config, registrar=FakeRegistrar())

    assert not service.arm_test(ACTION_READ)
