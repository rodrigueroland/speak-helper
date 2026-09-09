"""Map technical service failures to safe localized user messages."""

from __future__ import annotations

from .i18n import Translator


def localize_speech_error(translator: Translator, reason: str) -> str:
    """Return an actionable message without exposing raw server response bodies."""
    lowered = reason.casefold()
    if "connection refused" in lowered or "connect" in lowered:
        key = "error.speech_connection"
    elif "timed out" in lowered or "timeout" in lowered:
        key = "error.speech_timeout"
    elif lowered.startswith("http "):
        key = "error.speech_http"
    elif "audio format" in lowered or "content type" in lowered or "empty audio" in lowered:
        key = "error.speech_response"
    else:
        key = "error.speech"
    return translator.text(key)


def localize_ocr_error(translator: Translator, reason: str) -> str:
    if reason == "ocr_api_key":
        return translator.text("error.ocr_api_key")
    if reason == "ocr_no_text":
        return translator.text("ocr.no_text")
    return translator.text("error.ocr")


def localize_audio_error(translator: Translator, code: str) -> str:
    key = "error.audio_invalid" if code == "audio_invalid" else "error.audio"
    return translator.text(key)
