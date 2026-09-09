"""Theme token and stylesheet tests."""

from speak_helper.ui.theme import DARK, LIGHT, palette_for_theme, stylesheet_for_theme


def test_explicit_theme_selection_is_deterministic() -> None:
    assert palette_for_theme("light") is LIGHT
    assert palette_for_theme("dark") is DARK


def test_dark_stylesheet_uses_dark_semantic_tokens() -> None:
    stylesheet = stylesheet_for_theme("dark")
    assert DARK.surface in stylesheet
    assert DARK.text in stylesheet
    assert DARK.selection in stylesheet
