"""Loopback integration tests for the OpenAI-compatible TTS contract."""

from __future__ import annotations

import io
import json
import threading
import wave
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

import pytest

from speak_helper.config import Config
from speak_helper.speech_service import _ChunkWorker


def _silent_wav() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(b"\x00\x00" * 1_600)
    return output.getvalue()


class _TtsHandler(BaseHTTPRequestHandler):
    requests: ClassVar[list[dict[str, Any]]] = []

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        type(self).requests.append(
            {
                "path": self.path,
                "authorization": self.headers.get("Authorization"),
                "payload": payload,
            }
        )
        content = _silent_wav()
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, _format: str, *args: object) -> None:
        del args


@pytest.fixture
def local_tts_server() -> Iterator[str]:
    _TtsHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _TtsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/v1"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.parametrize(
    ("preset", "model", "voice", "expected_language"),
    [
        ("custom", "local-tts-model", "speaker-a", None),
        ("qwen3_local", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice", "Vivian", "French"),
    ],
)
def test_real_loopback_transport_supports_custom_and_qwen_presets(
    tmp_path: Path,
    monkeypatch,
    local_tts_server: str,
    preset: str,
    model: str,
    voice: str,
    expected_language: str | None,
) -> None:
    monkeypatch.setattr("speak_helper.config._HAS_KEYRING", False)
    config = Config(tmp_path, locale_name="en_US")
    config.set("tts", "backend", "openai")
    config.set("tts", "base_url", local_tts_server)
    config.set("tts", "model", model)
    config.set("tts", "voice", voice)
    config.set("tts", "provider_preset", preset)
    config.set("ui", "language", "fr")
    config.set("tts", "format", "wav")
    config.set("cache", "enabled", False)

    path = Path(_ChunkWorker("Bonjour from Codex", 0, 1, config)._fetch())
    try:
        assert path.read_bytes().startswith(b"RIFF")
    finally:
        path.unlink(missing_ok=True)

    request = _TtsHandler.requests[-1]
    assert request["path"] == "/v1/audio/speech"
    assert request["authorization"] is None
    expected_payload = {
        "model": model,
        "input": "Bonjour from Codex",
        "voice": voice,
        "speed": 1.0,
        "response_format": "wav",
    }
    if expected_language:
        expected_payload["language"] = expected_language
    assert request["payload"] == expected_payload
