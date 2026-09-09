"""Configuration defaults, validation, and migration tests."""

import json
from unittest.mock import MagicMock

from speak_helper.config import CONFIG_VERSION, Config, detect_system_language


def test_locale_detection() -> None:
    assert detect_system_language("fr_BE") == "fr"
    assert detect_system_language("fr-FR") == "fr"
    assert detect_system_language("en_US") == "en"
    assert detect_system_language("de_DE") == "en"


def test_new_french_configuration_uses_french_voice(tmp_path) -> None:
    config = Config(tmp_path, locale_name="fr_BE")

    assert config.language == "fr"
    assert config.edge_voice == "fr-FR-DeniseNeural"
    assert config.mode == "manual"
    assert not config.ocr_enabled


def test_version_one_configuration_is_preserved_and_migrated(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps(
            {"trigger": {"mode": "ask", "hotkey": "ctrl+alt+r"}, "tts": {"model": "legacy"}}
        ),
        encoding="utf-8",
    )

    config = Config(tmp_path, locale_name="en_US")
    config.save()
    saved = json.loads(path.read_text(encoding="utf-8"))

    assert config.mode == "ask"
    assert config.model == "legacy"
    assert saved["config_version"] == CONFIG_VERSION
    assert saved["ui"]["language"] == "en"


def test_invalid_values_use_safe_defaults(tmp_path) -> None:
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "ui": {"language": "zh", "theme": "neon"},
                "trigger": {"mode": "surprise", "max_length": "bad"},
                "tts": {"backend": "unknown", "speed": 99},
            }
        ),
        encoding="utf-8",
    )

    config = Config(tmp_path, locale_name="fr_BE")

    assert config.language == "en"
    assert config.mode == "manual"
    assert config.backend == "edge"
    assert config.speed == 2.0
    assert config.max_length == 20_000


def test_explicit_environment_config_directory(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("SPEAK_HELPER_CONFIG_DIR", str(tmp_path))
    config = Config(locale_name="en_US")
    config.save()

    assert config.path == tmp_path / "config.json"
    assert config.path.exists()


def test_api_key_uses_system_keyring_without_plaintext_copy(monkeypatch, tmp_path) -> None:
    import speak_helper.config as config_module

    credential_store = MagicMock()
    credential_store.get_password.return_value = "secret-value"
    monkeypatch.setattr(config_module, "_HAS_KEYRING", True)
    monkeypatch.setattr(config_module, "keyring", credential_store)
    config = Config(tmp_path, locale_name="en_US")

    config.api_key = "secret-value"
    config.save()
    saved = json.loads(config.path.read_text(encoding="utf-8"))

    credential_store.set_password.assert_called_once_with("speak_helper", "api_key", "secret-value")
    assert saved["tts"]["api_key"] == ""
    assert config.api_key == "secret-value"


def test_api_key_falls_back_to_config_when_keyring_fails(monkeypatch, tmp_path) -> None:
    import speak_helper.config as config_module

    credential_store = MagicMock()
    credential_store.set_password.side_effect = RuntimeError("unavailable")
    monkeypatch.setattr(config_module, "_HAS_KEYRING", True)
    monkeypatch.setattr(config_module, "keyring", credential_store)
    config = Config(tmp_path, locale_name="en_US")

    config.api_key = "fallback-value"

    assert config.get("tts", "api_key") == "fallback-value"
    assert config.api_key == "fallback-value"
