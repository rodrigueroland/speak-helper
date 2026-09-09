"""Technical text normalization tests."""

from speak_helper.text_normalizer import NormalizationOptions, normalize_for_speech


def test_markdown_and_french_unicode_are_preserved() -> None:
    source = "# Résumé\r\n\r\n- Élément naïf\r\n- Déjà vu"
    assert normalize_for_speech(source) == "Résumé\n\nÉlément naïf\nDéjà vu"


def test_code_content_is_preserved_without_fence_markers() -> None:
    source = "```python\nprint('bonjour')\n```"
    assert normalize_for_speech(source) == "print('bonjour')"


def test_code_can_be_omitted_explicitly() -> None:
    source = "Before\n```python\nprint('secret')\n```\nAfter"
    options = NormalizationOptions(preserve_code=False)
    assert normalize_for_speech(source, options) == "Before\n\nAfter"


def test_url_modes() -> None:
    source = "See https://docs.example.com/a/very/long/path?q=1 now"
    assert "https://" in normalize_for_speech(source)
    assert normalize_for_speech(source, NormalizationOptions(url_mode="domain")) == (
        "See docs.example.com now"
    )
    assert normalize_for_speech(source, NormalizationOptions(url_mode="omit")) == "See link now"


def test_preprocessing_can_be_disabled_without_altering_content() -> None:
    source = "# Heading\r\n\r\n- item   with spaces"

    assert normalize_for_speech(source, NormalizationOptions(enabled=False)) == source
