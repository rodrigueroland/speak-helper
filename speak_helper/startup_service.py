"""Optional per-user launch-at-login integration."""

from __future__ import annotations

import importlib
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_VALUE_NAME = "Speak Helper"


@dataclass(frozen=True, slots=True)
class StartupResult:
    """Outcome of a launch-at-login configuration request."""

    success: bool
    reason: str = ""


def startup_command(executable: str | None = None, *, frozen: bool | None = None) -> str:
    """Build the command stored in the Windows per-user Run registry key."""
    selected_executable = executable or sys.executable
    selected_frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    arguments = [selected_executable]
    if not selected_frozen:
        arguments.extend(("-m", "speak_helper"))
    return subprocess.list2cmdline(arguments)


class StartupService:
    """Manage launch-at-login without requiring administrator privileges."""

    def __init__(
        self,
        *,
        platform_name: str | None = None,
        executable: str | None = None,
        frozen: bool | None = None,
    ) -> None:
        self._platform_name = platform_name or sys.platform
        self._command = startup_command(executable, frozen=frozen)

    @property
    def supported(self) -> bool:
        return self._platform_name == "win32"

    @property
    def command(self) -> str:
        return self._command

    def is_enabled(self) -> bool:
        if not self.supported:
            return False
        winreg: Any = importlib.import_module("winreg")

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
                value, _value_type = winreg.QueryValueEx(key, _VALUE_NAME)
        except OSError:
            return False
        return str(value) == self._command

    def set_enabled(self, enabled: bool) -> StartupResult:
        if not self.supported:
            return StartupResult(not enabled, "unsupported platform" if enabled else "")

        winreg: Any = importlib.import_module("winreg")

        try:
            if enabled:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
                    winreg.SetValueEx(key, _VALUE_NAME, 0, winreg.REG_SZ, self._command)
            else:
                try:
                    with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
                    ) as key:
                        winreg.DeleteValue(key, _VALUE_NAME)
                except FileNotFoundError:
                    pass
        except OSError as exc:
            return StartupResult(False, str(exc))
        return StartupResult(True)
