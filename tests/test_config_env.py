"""Config .env fallback — model vars optional when set in Settings."""

import json

from speak_helper.config import DEFAULT, Config


def _make_config(tmp_path, cfg_file, monkeypatch):
    import speak_helper.config as cfg_mod

    monkeypatch.setattr(cfg_mod, "_env_dotenv_loaded", True)

    class _Cfg(Config):
        def __init__(self) -> None:
            self._dir = tmp_path
            self._file = cfg_file
            self._data = json.loads(json.dumps(DEFAULT))
            self._load()

    return _Cfg()


def test_env_model_applies_when_not_in_saved_config(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEAK_HELPER_TTS_MODEL", "env-only-model")
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text('{"tts": {"api_key": "from-json"}}', encoding="utf-8")

    c = _make_config(tmp_path, cfg_file, monkeypatch)
    assert c.model == "env-only-model"


def test_saved_config_model_overrides_env(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEAK_HELPER_TTS_MODEL", "env-model")
    cfg_file = tmp_path / "config.json"
    cfg_file.write_text(
        '{"tts": {"model": "saved-model", "api_key": "k"}}',
        encoding="utf-8",
    )

    c = _make_config(tmp_path, cfg_file, monkeypatch)
    assert c.model == "saved-model"
