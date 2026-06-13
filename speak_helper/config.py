"""配置管理：加载/保存 JSON，API Key 用 keyring 存储；.env 可选兜底"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from platformdirs import user_config_dir

_env_dotenv_loaded = False

try:
    import keyring
    _HAS_KEYRING = True
except Exception:
    _HAS_KEYRING = False

_KEYRING_SERVICE = "speak_helper"
_KEYRING_KEY = "api_key"

DEFAULT: dict[str, Any] = {
    "tts": {
        "backend": "edge",                          # "edge" | "openai"
        # Edge-TTS 配置（无需 API Key，使用微软免费服务）
        "edge_voice": "zh-CN-XiaoxiaoNeural",
        # OpenAI 兼容 API 配置
        "base_url": "https://api.siliconflow.cn/v1",
        "model": "FunAudioLLM/CosyVoice2-0.5B",
        "voice": "FunAudioLLM/CosyVoice2-0.5B:anna",
        "speed": 1.2,
        "format": "mp3",
        "timeout_sec": 30,
        "sentences_per_chunk": 3,
    },
    "trigger": {
        "clipboard_enabled": True,
        "hotkey_enabled": True,
        "hotkey": "ctrl+alt+r",
        "mode": "ask",          # "ask" | "auto"
        "min_length": 2,
        "max_length": 2000,
        "debounce_ms": 200,
    },
    "ui": {
        "dock_x": None,
        "dock_y": None,
        "dock_edge": "right",   # "right" | "left"
        "bubble_timeout_ms": 6000,
        "theme": "system",      # "system" | "dark" | "light"
        "autostart": False,
    },
    "cache": {
        "enabled": True,
        "max_mb": 100,
    },
    "ocr": {
        "enabled": True,
        "model": "PaddlePaddle/PaddleOCR-VL-1.5",
        # 图片压缩质量（0-95），越低文件越小，API 消耗越少
        "image_quality": 85,
    },
}


def _deep_merge(base: dict, override: dict) -> None:
    for k, v in override.items():
        if k in base and isinstance(base[k], dict) and isinstance(v, dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v


def _saved_nonempty(saved: dict, *keys: str) -> bool:
    """config.json 中该键已有非空值时，不再用 .env 覆盖。"""
    d: Any = saved
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return False
        d = d[k]
    if d is None:
        return False
    return str(d).strip() != ""


def _load_dotenv_files(config_dir: Path) -> None:
    """按优先级加载首个存在的 .env（不覆盖已有环境变量）。"""
    global _env_dotenv_loaded
    if _env_dotenv_loaded:
        return
    _env_dotenv_loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    pkg_root = Path(__file__).resolve().parents[1]
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / ".env")
    candidates.extend([
        config_dir / ".env",
        pkg_root / ".env",
        pkg_root.parent / ".env",
    ])
    seen: set[str] = set()
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.exists():
            load_dotenv(path, override=False)
            break


def _apply_env_fallback(data: dict[str, Any], saved: dict[str, Any], config_dir: Path) -> None:
    """
    可选 .env 兜底。优先级：设置面板 / config.json > .env > DEFAULT。
    模型相关变量（TTS_MODEL / OCR_MODEL 等）均为可选，可在设置中配置。
    """
    _load_dotenv_files(config_dir)

    mappings: list[tuple[tuple[str, ...], tuple[str, ...]]] = [
        (("tts", "backend"), ("SPEAK_HELPER_TTS_BACKEND", "TTS_BACKEND")),
        (("tts", "base_url"), ("SPEAK_HELPER_BASE_URL", "TTS_BASE_URL", "BASE_URL")),
        (("tts", "api_key"), ("SPEAK_HELPER_API_KEY", "TTS_API_KEY", "API_KEY")),
        (("tts", "model"), ("SPEAK_HELPER_TTS_MODEL", "TTS_MODEL")),
        (("tts", "voice"), ("SPEAK_HELPER_TTS_VOICE", "TTS_VOICE")),
        (("tts", "edge_voice"), ("SPEAK_HELPER_EDGE_VOICE", "EDGE_VOICE")),
        (("ocr", "model"), ("SPEAK_HELPER_OCR_MODEL", "OCR_MODEL")),
    ]
    for keys, env_names in mappings:
        if _saved_nonempty(saved, *keys):
            continue
        for name in env_names:
            val = os.getenv(name, "").strip()
            if val:
                d = data
                for k in keys[:-1]:
                    d = d.setdefault(k, {})
                d[keys[-1]] = val
                break


class Config:
    def __init__(self) -> None:
        self._dir = Path(user_config_dir("speak_helper"))
        self._file = self._dir / "config.json"
        self._data: dict[str, Any] = json.loads(json.dumps(DEFAULT))
        self._load()

    # ── persistence ──────────────────────────────────────────────────────────

    def _load(self) -> None:
        saved: dict[str, Any] = {}
        if self._file.exists():
            try:
                saved = json.loads(self._file.read_text(encoding="utf-8"))
                if isinstance(saved, dict):
                    _deep_merge(self._data, saved)
            except Exception:
                saved = {}
        _apply_env_fallback(self._data, saved, self._dir)

    def save(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        self._file.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def reload(self) -> None:
        """从磁盘重新加载配置到内存（settings 保存后调用）"""
        self._data = json.loads(json.dumps(DEFAULT))
        self._load()  # 含 .env 兜底（config.json 优先）

    # ── generic get/set ──────────────────────────────────────────────────────

    def get(self, *keys: str, default: Any = None) -> Any:
        d = self._data
        for k in keys:
            if not isinstance(d, dict) or k not in d:
                return default
            d = d[k]
        return d

    def set(self, *keys_value) -> None:
        """set("tts", "speed", 1.5)"""
        keys, value = keys_value[:-1], keys_value[-1]
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value

    # ── API key (keyring first, fallback to config) ───────────────────────────

    @property
    def api_key(self) -> str:
        # JSON 优先（最可靠），keyring 仅作额外备份
        val = self._data.get("tts", {}).get("api_key", "").strip()
        if val:
            return val
        if _HAS_KEYRING:
            try:
                kr_val = keyring.get_password(_KEYRING_SERVICE, _KEYRING_KEY)
                if kr_val:
                    return kr_val.strip()
            except Exception:
                pass
        return ""

    @api_key.setter
    def api_key(self, value: str) -> None:
        value = value.strip()
        # 主存储：JSON 文件
        self.set("tts", "api_key", value)
        self.save()
        # 副存储：keyring（失败不影响主流程）
        if _HAS_KEYRING:
            try:
                keyring.set_password(_KEYRING_SERVICE, _KEYRING_KEY, value)
            except Exception:
                pass

    # ── convenience properties ────────────────────────────────────────────────

    @property
    def base_url(self) -> str:
        return self.get("tts", "base_url", default="https://api.openai.com/v1")

    @property
    def model(self) -> str:
        return self.get("tts", "model", default="tts-1")

    @property
    def voice(self) -> str:
        return self.get("tts", "voice", default="nova")

    @property
    def speed(self) -> float:
        return float(self.get("tts", "speed", default=1.2))

    @property
    def backend(self) -> str:
        return self.get("tts", "backend", default="edge")

    @property
    def edge_voice(self) -> str:
        return self.get("tts", "edge_voice", default="zh-CN-XiaoxiaoNeural")

    @property
    def sentences_per_chunk(self) -> int:
        return int(self.get("tts", "sentences_per_chunk", default=3))

    @property
    def audio_format(self) -> str:
        return self.get("tts", "format", default="mp3")

    @property
    def timeout_sec(self) -> int:
        return int(self.get("tts", "timeout_sec", default=30))

    @property
    def clipboard_enabled(self) -> bool:
        return bool(self.get("trigger", "clipboard_enabled", default=True))

    @property
    def hotkey_enabled(self) -> bool:
        return bool(self.get("trigger", "hotkey_enabled", default=True))

    @property
    def hotkey(self) -> str:
        return self.get("trigger", "hotkey", default="ctrl+alt+r")

    @property
    def mode(self) -> str:
        return self.get("trigger", "mode", default="ask")

    @property
    def min_length(self) -> int:
        return int(self.get("trigger", "min_length", default=2))

    @property
    def max_length(self) -> int:
        return int(self.get("trigger", "max_length", default=2000))

    @property
    def debounce_ms(self) -> int:
        return int(self.get("trigger", "debounce_ms", default=200))

    @property
    def bubble_timeout_ms(self) -> int:
        return int(self.get("ui", "bubble_timeout_ms", default=6000))

    @property
    def dock_edge(self) -> str:
        return self.get("ui", "dock_edge", default="right")

    @property
    def cache_enabled(self) -> bool:
        return bool(self.get("cache", "enabled", default=True))

    @property
    def cache_max_mb(self) -> int:
        return int(self.get("cache", "max_mb", default=100))

    @property
    def cache_dir(self) -> Path:
        d = self._dir / "cache"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── OCR ──────────────────────────────────────────────────────────────────

    @property
    def ocr_enabled(self) -> bool:
        return bool(self.get("ocr", "enabled", default=True))

    @property
    def ocr_model(self) -> str:
        return self.get("ocr", "model", default="PaddlePaddle/PaddleOCR-VL-1.5")

    @property
    def ocr_image_quality(self) -> int:
        return int(self.get("ocr", "image_quality", default=85))
