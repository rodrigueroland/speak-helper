"""Launch-at-login service tests without touching the host registry."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import patch

from speak_helper.startup_service import StartupService, startup_command


def test_startup_command_for_packaged_application_quotes_spaces() -> None:
    command = startup_command(r"C:\Program Files\Speak Helper\SpeakHelper.exe", frozen=True)

    assert command == '"C:\\Program Files\\Speak Helper\\SpeakHelper.exe"'


def test_startup_command_for_development_uses_module_entrypoint() -> None:
    command = startup_command(r"C:\Python\python.exe", frozen=False)

    assert command == r"C:\Python\python.exe -m speak_helper"


def test_unsupported_platform_can_only_disable() -> None:
    service = StartupService(platform_name="linux", frozen=True)

    assert not service.is_enabled()
    assert not service.set_enabled(True).success
    assert service.set_enabled(False).success


class _FakeKey:
    def __enter__(self):
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_windows_registry_round_trip() -> None:
    values: dict[str, str] = {}

    def query_value(_key: object, name: str) -> tuple[str, int]:
        if name not in values:
            raise FileNotFoundError
        return values[name], 1

    fake_winreg = SimpleNamespace(
        HKEY_CURRENT_USER=object(),
        KEY_SET_VALUE=2,
        REG_SZ=1,
        OpenKey=lambda *_args: _FakeKey(),
        CreateKey=lambda *_args: _FakeKey(),
        QueryValueEx=query_value,
        SetValueEx=lambda _key, name, _reserved, _type, value: values.__setitem__(name, value),
        DeleteValue=lambda _key, name: values.pop(name),
    )
    service = StartupService(
        platform_name="win32", executable=r"C:\Apps\SpeakHelper.exe", frozen=True
    )

    with patch.dict(sys.modules, {"winreg": fake_winreg}):
        assert not service.is_enabled()
        assert service.set_enabled(True).success
        assert service.is_enabled()
        assert service.set_enabled(False).success
        assert not service.is_enabled()
