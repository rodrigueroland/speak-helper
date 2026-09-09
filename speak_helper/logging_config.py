"""Privacy-conscious rotating application logging."""

from __future__ import annotations

import json
import logging
import logging.handlers
from datetime import UTC, datetime
from pathlib import Path


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(log_dir: Path) -> Path:
    """Configure one bounded UTF-8 JSON-lines log and return its path."""
    log_dir.mkdir(parents=True, exist_ok=True)
    path = log_dir / "speak-helper.log"
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in tuple(root.handlers):
        root.removeHandler(handler)
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    return path
