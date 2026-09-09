"""Versioned, validated application configuration."""

from __future__ import annotations

import contextlib
import copy
import json
import locale
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

try:
    import keyring

    _HAS_KEYRING = True
except Exception:  # pragma: no cover - host credential backend
    _HAS_KEYRING = False

CONFIG_VERSION = 2
SUPPORTED_LANGUAGES = ("en", "fr")
_KEYRING_SERVICE = "speak_helper"
_KEYRING_KEY = "api_key"
_env_dotenv_loaded = False

DEFAULT: dict[str, Any] = {
    "config_version": CONFIG_VERSION,
    "tts": {
        "backend": "edge",
        "provider_preset": "custom",
        "edge_voice": "en-US-AriaNeural",
        "base_url": "http://127.0.0.1:8000/v1",
        "model": "tts-1",
        "voice": "alloy",
        "api_key": "",
        "speed": 1.0,
        "format": "mp3",
        "timeout_sec": 30,
        "sentences_per_chunk": 3,
    },
    "trigger": {
        "clipboard_enabled": False,
        "hotkey_enabled": True,
        "hotkey": "ctrl+alt+r",
        "stop_hotkey": "ctrl+alt+shift+x",
        "pause_hotkey": "ctrl+alt+shift+p",
        "replay_hotkey": "ctrl+alt+shift+r",
        "mode": "manual",
        "min_length": 1,
        "max_length": 20_000,
        "debounce_ms": 200,
    },
    "clipboard": {
        "restore_after_capture": True,
        "capture_timeout_ms": 1_500,
        "poll_interval_ms": 25,
    },
    "preprocessing": {
        "enabled": True,
        "strip_markdown_markers": True,
        "preserve_code": True,
        "url_mode": "keep",
    },
    "ui": {
        "language": "en",
        "dock_x": None,
        "dock_y": None,
        "dock_edge": "right",
        "bubble_timeout_ms": 6_000,
        "theme": "system",
        "autostart": False,
    },
    "cache": {"enabled": True, "max_mb": 100},
    "ocr": {
        "enabled": False,
        "model": "PaddlePaddle/PaddleOCR-VL-1.5",
        "image_quality": 85,
    },
}


def detect_system_language(locale_name: str | None = None) -> str:
    """Map an OS locale to a supported product language."""
    candidate = locale_name or locale.getlocale()[0] or os.getenv("LANG", "") or ""
    normalized = candidate.replace("-", "_").lower()
    return "fr" if normalized == "fr" or normalized.startswith("fr_") else "en"


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def _saved_nonempty(saved: dict[str, Any], *keys: str) -> bool:
    current: Any = saved
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return False
        current = current[key]
    return current is not None and str(current).strip() != ""


def _load_dotenv_files(config_dir: Path) -> None:
    global _env_dotenv_loaded
    if _env_dotenv_loaded:
        return
    _env_dotenv_loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover
        return
    package_root = Path(__file__).resolve().parents[1]
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / ".env")
    candidates.extend((config_dir / ".env", package_root / ".env", package_root.parent / ".env"))
    for path in dict.fromkeys(candidates):
        if path.exists():
            load_dotenv(path, override=False)
            return


def _apply_env_fallback(data: dict[str, Any], saved: dict[str, Any], config_dir: Path) -> None:
    _load_dotenv_files(config_dir)
    mappings = (
        (("tts", "backend"), ("SPEAK_HELPER_TTS_BACKEND", "TTS_BACKEND")),
        (("tts", "base_url"), ("SPEAK_HELPER_BASE_URL", "TTS_BASE_URL", "BASE_URL")),
        (("tts", "api_key"), ("SPEAK_HELPER_API_KEY", "TTS_API_KEY", "API_KEY")),
        (("tts", "model"), ("SPEAK_HELPER_TTS_MODEL", "TTS_MODEL")),
        (("tts", "voice"), ("SPEAK_HELPER_TTS_VOICE", "TTS_VOICE")),
        (("tts", "edge_voice"), ("SPEAK_HELPER_EDGE_VOICE", "EDGE_VOICE")),
        (("ocr", "model"), ("SPEAK_HELPER_OCR_MODEL", "OCR_MODEL")),
    )
    for keys, environment_names in mappings:
        if _saved_nonempty(saved, *keys):
            continue
        for name in environment_names:
            value = os.getenv(name, "").strip()
            if value:
                destination = data
                for key in keys[:-1]:
                    destination = destination.setdefault(key, {})
                destination[keys[-1]] = value
                break


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default


def _bounded_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    try:
        return max(minimum, min(maximum, float(value)))
    except (TypeError, ValueError):
        return default


class Config:
    """JSON-backed configuration with backward-compatible migrations."""

    def __init__(self, config_dir: Path | None = None, locale_name: str | None = None) -> None:
        self._dir = config_dir or Path(user_config_dir("speak_helper"))
        self._file = self._dir / "config.json"
        self._locale_name = locale_name
        self._data: dict[str, Any] = copy.deepcopy(DEFAULT)
        self._load()

    @property
    def path(self) -> Path:
        return self._file

    @property
    def config_dir(self) -> Path:
        return self._dir

    def _load(self) -> None:
        saved: dict[str, Any] = {}
        if self._file.exists():
            try:
                raw = json.loads(self._file.read_text(encoding="utf-8"))
                if isinstance(raw, dict):
                    saved = raw
            except (OSError, UnicodeError, json.JSONDecodeError):
                saved = {}
        _deep_merge(self._data, saved)
        if not _saved_nonempty(saved, "ui", "language"):
            language = detect_system_language(getattr(self, "_locale_name", None))
            self.set("ui", "language", language)
            if not saved and language == "fr":
                self.set("tts", "edge_voice", "fr-FR-DeniseNeural")
        self._migrate(saved)
        self._validate()
        _apply_env_fallback(self._data, saved, self._dir)

    def _migrate(self, saved: dict[str, Any]) -> None:
        version = _bounded_int(saved.get("config_version", 1), 1, 1, CONFIG_VERSION)
        if version < 2 and self.mode not in {"ask", "auto", "manual"}:
            self.set("trigger", "mode", "manual")
        self._data["config_version"] = CONFIG_VERSION

    def _validate(self) -> None:
        if self.language not in SUPPORTED_LANGUAGES:
            self.set("ui", "language", "en")
        if self.backend not in {"edge", "openai"}:
            self.set("tts", "backend", "edge")
        if self.mode not in {"manual", "ask", "auto"}:
            self.set("trigger", "mode", "manual")
        if self.get("ui", "theme") not in {"system", "light", "dark"}:
            self.set("ui", "theme", "system")
        if self.get("preprocessing", "url_mode") not in {"keep", "domain", "omit"}:
            self.set("preprocessing", "url_mode", "keep")
        self.set("tts", "speed", self.speed)
        self.set("tts", "timeout_sec", self.timeout_sec)
        self.set("trigger", "min_length", self.min_length)
        self.set("trigger", "max_length", self.max_length)
        self.set("trigger", "debounce_ms", self.debounce_ms)

    def save(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        temporary = self._file.with_suffix(".json.tmp")
        temporary.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        try:
            temporary.replace(self._file)
        except PermissionError:
            # Some synchronized Windows folders briefly deny atomic replacement.
            # Preserve a usable save path while keeping the temporary write first.
            shutil.copyfile(temporary, self._file)
            temporary.unlink()

    def reload(self) -> None:
        self._data = copy.deepcopy(DEFAULT)
        self._load()

    def get(self, *keys: str, default: Any = None) -> Any:
        current: Any = self._data
        for key in keys:
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current

    def set(self, *keys_value: Any) -> None:
        if len(keys_value) < 2:
            raise ValueError("set requires at least one key and a value")
        keys, value = keys_value[:-1], keys_value[-1]
        destination = self._data
        for key in keys[:-1]:
            destination = destination.setdefault(str(key), {})
        destination[str(keys[-1])] = value

    @property
    def api_key(self) -> str:
        value = str(self.get("tts", "api_key", default="")).strip()
        if value:
            return value
        if _HAS_KEYRING:
            try:
                return (keyring.get_password(_KEYRING_SERVICE, _KEYRING_KEY) or "").strip()
            except Exception:  # pragma: no cover
                return ""
        return ""

    @api_key.setter
    def api_key(self, value: str) -> None:
        clean_value = value.strip()
        self.set("tts", "api_key", clean_value)
        if _HAS_KEYRING and clean_value:
            with contextlib.suppress(Exception):  # pragma: no cover - host keyring
                keyring.set_password(_KEYRING_SERVICE, _KEYRING_KEY, clean_value)

    @property
    def language(self) -> str:
        return str(self.get("ui", "language", default="en"))

    @property
    def base_url(self) -> str:
        return str(self.get("tts", "base_url", default="http://127.0.0.1:8000/v1"))

    @property
    def model(self) -> str:
        return str(self.get("tts", "model", default="tts-1"))

    @property
    def voice(self) -> str:
        return str(self.get("tts", "voice", default="alloy"))

    @property
    def speed(self) -> float:
        return _bounded_float(self.get("tts", "speed"), 1.0, 0.5, 2.0)

    @property
    def backend(self) -> str:
        return str(self.get("tts", "backend", default="edge"))

    @property
    def edge_voice(self) -> str:
        return str(self.get("tts", "edge_voice", default="en-US-AriaNeural"))

    @property
    def sentences_per_chunk(self) -> int:
        return _bounded_int(self.get("tts", "sentences_per_chunk"), 3, 1, 20)

    @property
    def audio_format(self) -> str:
        return str(self.get("tts", "format", default="mp3"))

    @property
    def timeout_sec(self) -> int:
        return _bounded_int(self.get("tts", "timeout_sec"), 30, 1, 300)

    @property
    def clipboard_enabled(self) -> bool:
        return bool(self.get("trigger", "clipboard_enabled", default=False))

    @property
    def hotkey_enabled(self) -> bool:
        return bool(self.get("trigger", "hotkey_enabled", default=True))

    @property
    def hotkey(self) -> str:
        return str(self.get("trigger", "hotkey", default="ctrl+alt+r"))

    @property
    def stop_hotkey(self) -> str:
        return str(self.get("trigger", "stop_hotkey", default="ctrl+alt+shift+x"))

    @property
    def pause_hotkey(self) -> str:
        return str(self.get("trigger", "pause_hotkey", default="ctrl+alt+shift+p"))

    @property
    def replay_hotkey(self) -> str:
        return str(self.get("trigger", "replay_hotkey", default="ctrl+alt+shift+r"))

    @property
    def mode(self) -> str:
        return str(self.get("trigger", "mode", default="manual"))

    @property
    def min_length(self) -> int:
        return _bounded_int(self.get("trigger", "min_length"), 1, 1, 1_000)

    @property
    def max_length(self) -> int:
        return _bounded_int(self.get("trigger", "max_length"), 20_000, 10, 200_000)

    @property
    def debounce_ms(self) -> int:
        return _bounded_int(self.get("trigger", "debounce_ms"), 200, 0, 5_000)

    @property
    def capture_timeout_ms(self) -> int:
        return _bounded_int(self.get("clipboard", "capture_timeout_ms"), 1_500, 250, 10_000)

    @property
    def clipboard_poll_interval_ms(self) -> int:
        return _bounded_int(self.get("clipboard", "poll_interval_ms"), 25, 10, 250)

    @property
    def restore_clipboard(self) -> bool:
        return bool(self.get("clipboard", "restore_after_capture", default=True))

    @property
    def bubble_timeout_ms(self) -> int:
        return _bounded_int(self.get("ui", "bubble_timeout_ms"), 6_000, 1_000, 60_000)

    @property
    def dock_edge(self) -> str:
        return str(self.get("ui", "dock_edge", default="right"))

    @property
    def cache_enabled(self) -> bool:
        return bool(self.get("cache", "enabled", default=True))

    @property
    def cache_max_mb(self) -> int:
        return _bounded_int(self.get("cache", "max_mb"), 100, 0, 10_000)

    @property
    def cache_dir(self) -> Path:
        path = self._dir / "cache"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_dir(self) -> Path:
        path = self._dir / "logs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def ocr_enabled(self) -> bool:
        return bool(self.get("ocr", "enabled", default=False))

    @property
    def ocr_model(self) -> str:
        return str(self.get("ocr", "model", default="PaddlePaddle/PaddleOCR-VL-1.5"))

    @property
    def ocr_image_quality(self) -> int:
        return _bounded_int(self.get("ocr", "image_quality"), 85, 30, 95)
