"""Safe runtime diagnostics without credentials or clipboard content."""

from __future__ import annotations

import platform
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from . import __version__
from .audio_player import AudioPlayer
from .clipboard_watcher import ClipboardWatcher
from .config import Config
from .hotkey_service import ACTION_READ, HotkeyService


@dataclass(frozen=True, slots=True)
class DiagnosticsSnapshot:
    app_version: str
    operating_system: str
    python_version: str
    language: str
    read_hotkey: str
    hotkey_registered: bool
    hotkey_detail: str
    clipboard_watcher_active: bool
    tts_backend: str
    tts_endpoint: str
    tts_model: str
    audio_state: str
    cache_path: str
    log_path: str


def collect_diagnostics(
    config: Config,
    hotkeys: HotkeyService,
    clipboard_watcher: ClipboardWatcher,
    player: AudioPlayer,
    log_path: Path,
) -> DiagnosticsSnapshot:
    registration = hotkeys.results.get(ACTION_READ)
    return DiagnosticsSnapshot(
        app_version=__version__,
        operating_system=f"{platform.system()} {platform.release()} ({platform.machine()})",
        python_version=platform.python_version()
        if not getattr(sys, "frozen", False)
        else "Bundled",
        language=config.language,
        read_hotkey=config.hotkey,
        hotkey_registered=bool(registration and registration.registered),
        hotkey_detail=registration.reason if registration else "not started",
        clipboard_watcher_active=clipboard_watcher.active,
        tts_backend=config.backend,
        tts_endpoint="Microsoft Edge TTS" if config.backend == "edge" else config.base_url,
        tts_model="Edge voice" if config.backend == "edge" else config.model,
        audio_state=player.state,
        cache_path=str(config.cache_dir),
        log_path=str(log_path),
    )


def format_diagnostics(snapshot: DiagnosticsSnapshot) -> str:
    return "\n".join(f"{key}: {value}" for key, value in asdict(snapshot).items())
