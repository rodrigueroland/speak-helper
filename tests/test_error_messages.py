"""Localized service error mapping tests."""

import pytest

from speak_helper.config import Config
from speak_helper.error_messages import (
    localize_audio_error,
    localize_ocr_error,
    localize_speech_error,
)
from speak_helper.i18n import Translator


@pytest.fixture
def french_translator(tmp_path) -> Translator:
    config = Config(tmp_path, locale_name="fr_FR")
    return Translator(config)


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("Connection refused: local server", "Connexion impossible"),
        ("Request timed out after 10 seconds", "délai imparti"),
        ("HTTP 503: secret response body", "erreur HTTP"),
        ("unsupported content type application/json", "non valide"),
        ("unexpected internal detail", "paramètres et le diagnostic"),
    ],
)
def test_speech_failures_are_classified_without_leaking_details(
    french_translator: Translator, reason: str, expected: str
) -> None:
    message = localize_speech_error(french_translator, reason)
    assert expected in message
    assert "secret response body" not in message
    assert "unexpected internal detail" not in message


def test_ocr_and_audio_failures_are_localized(french_translator: Translator) -> None:
    assert localize_ocr_error(french_translator, "ocr_no_text").startswith("Aucun texte")
    assert "diagnostic" in localize_ocr_error(french_translator, "raw provider failure")
    assert "périphérique" in localize_audio_error(french_translator, "raw multimedia error")
