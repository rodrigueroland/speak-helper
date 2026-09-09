"""Diagnostics snapshot privacy and content tests."""

from types import SimpleNamespace

from speak_helper.config import Config
from speak_helper.diagnostics import collect_diagnostics, format_diagnostics
from speak_helper.hotkey_service import ACTION_READ, RegistrationResult


def test_diagnostics_include_runtime_state_without_credentials(tmp_path) -> None:
    config = Config(tmp_path, locale_name="fr_FR")
    config.set("tts", "backend", "openai")
    config.set("tts", "base_url", "http://127.0.0.1:8000/v1")
    config.set("tts", "api_key", "never-show-this-secret")
    hotkeys = SimpleNamespace(
        results={
            ACTION_READ: RegistrationResult(ACTION_READ, config.hotkey, True),
        }
    )
    watcher = SimpleNamespace(active=True)
    player = SimpleNamespace(state="paused", output_available=False, output_device="")

    snapshot = collect_diagnostics(config, hotkeys, watcher, player, tmp_path / "app.log")
    rendered = format_diagnostics(snapshot)

    assert snapshot.language == "fr"
    assert snapshot.hotkey_registered
    assert snapshot.tts_endpoint == "http://127.0.0.1:8000/v1"
    assert snapshot.audio_state == "paused"
    assert not snapshot.audio_output_available
    assert snapshot.audio_output_device == ""
    assert "never-show-this-secret" not in rendered
