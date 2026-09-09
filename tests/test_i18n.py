"""Localization catalog and fallback tests."""

from speak_helper.config import Config
from speak_helper.i18n import CATALOGS, EN, FR, Translator


def test_english_and_french_catalogs_are_complete() -> None:
    assert EN
    assert set(EN) == set(FR)
    assert all(value.strip() for catalog in CATALOGS.values() for value in catalog.values())


def test_unknown_language_and_key_fall_back_to_english(tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    translator = Translator(config)
    translator.set_language("unsupported", persist=False)

    assert translator.language == "en"
    assert translator.text("action.stop") == "Stop"
    assert translator.text("missing.key") == "missing.key"


def test_language_change_persists(tmp_path) -> None:
    config = Config(tmp_path, locale_name="en_US")
    translator = Translator(config)
    translator.set_language("fr")

    assert Config(tmp_path, locale_name="en_US").language == "fr"
