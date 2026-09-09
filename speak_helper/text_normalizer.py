"""Conservative, independently testable text preparation for speech."""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

_HEADING = re.compile(r"(?m)^[ \t]{0,3}#{1,6}[ \t]+")
_BULLET = re.compile(r"(?m)^[ \t]*(?:[-*+][ \t]+|\d+[.)][ \t]+)")
_FENCE = re.compile(r"(?m)^[ \t]*```[^\n]*\n?|^[ \t]*```[ \t]*$")
_URL = re.compile(r"https?://[^\s<>]+", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class NormalizationOptions:
    strip_markdown_markers: bool = True
    preserve_code: bool = True
    url_mode: str = "keep"


def normalize_for_speech(text: str, options: NormalizationOptions | None = None) -> str:
    """Normalize layout noise without removing technical meaning."""
    selected = options or NormalizationOptions()
    result = text.replace("\r\n", "\n").replace("\r", "\n")
    if not selected.preserve_code:
        result = re.sub(r"```.*?```", "", result, flags=re.DOTALL)
    if selected.strip_markdown_markers:
        result = _HEADING.sub("", result)
        result = _BULLET.sub("", result)
        result = _FENCE.sub("", result)
    if selected.url_mode == "omit":
        result = _URL.sub("link", result)
    elif selected.url_mode == "domain":
        result = _URL.sub(lambda match: urlsplit(match.group(0)).netloc or match.group(0), result)
    result = re.sub(r"[ \t]+", " ", result)
    result = re.sub(r" *\n *", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()
