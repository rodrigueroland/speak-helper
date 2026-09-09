"""Speech-service unit tests with mocked HTTP."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest


@pytest.fixture(autouse=True)
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_config(tmp_path: Path):
    cfg = MagicMock()
    cfg.backend = "openai"
    cfg.provider_preset = "custom"
    cfg.language = "en"
    cfg.api_key = "test-key"
    cfg.base_url = "https://api.openai.com/v1"
    cfg.model = "tts-1"
    cfg.voice = "nova"
    cfg.speed = 1.2
    cfg.audio_format = "mp3"
    cfg.timeout_sec = 10
    cfg.cache_enabled = True
    cfg.cache_max_mb = 10
    cfg.cache_dir = tmp_path
    return cfg


def test_cache_hit(tmp_path):
    import hashlib

    from speak_helper.speech_service import _ChunkWorker

    text = "hello"
    voice = "nova"
    model = "tts-1"
    speed = 1.2
    fmt = "mp3"
    base_url = "https://api.openai.com/v1"
    key = hashlib.sha1(
        f"{base_url}|custom|en|{text}|{voice}|{model}|{speed}|{fmt}".encode()
    ).hexdigest()
    cached_file = tmp_path / f"{key}.mp3"
    cached_file.write_bytes(b"fake_audio")

    cfg = _make_config(tmp_path)
    worker = _ChunkWorker(text, 0, 1, cfg)
    results = []
    worker.chunk_ready.connect(lambda path, _idx, _total: results.append(path))
    worker.run()
    assert results == [str(cached_file)]


def test_api_call_on_cache_miss(tmp_path):
    from speak_helper.speech_service import _ChunkWorker

    cfg = _make_config(tmp_path)
    worker = _ChunkWorker("new text", 0, 1, cfg)
    errors = []
    results = []
    worker.chunk_ready.connect(lambda path, _idx, _total: results.append(path))
    worker.error.connect(lambda msg, _idx, _total: errors.append(msg))

    fake_response = MagicMock()
    fake_response.content = b"audio_data"
    fake_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.post.return_value = fake_response
        worker.run()

    assert results and errors == []
    assert Path(results[0]).read_bytes() == b"audio_data"


def test_cancel_before_run(tmp_path):
    from speak_helper.speech_service import _ChunkWorker

    cfg = _make_config(tmp_path)
    worker = _ChunkWorker("hello", 0, 1, cfg)
    worker.cancel()
    results = []
    worker.chunk_ready.connect(lambda path, _idx, _total: results.append(path))
    worker.run()
    assert results == []


def test_local_endpoint_does_not_require_api_key(tmp_path):
    from speak_helper.speech_service import _ChunkWorker

    config = _make_config(tmp_path)
    config.api_key = ""
    fake_response = MagicMock(content=b"audio", headers={"content-type": "audio/mpeg"})
    fake_response.raise_for_status = MagicMock()

    with patch("httpx.Client") as client_class:
        post = client_class.return_value.__enter__.return_value.post
        post.return_value = fake_response
        _ChunkWorker("local text", 0, 1, config).run()

    assert "Authorization" not in post.call_args.kwargs["headers"]


def test_timeout_has_actionable_error(tmp_path):
    import httpx

    from speak_helper.speech_service import _ChunkWorker

    config = _make_config(tmp_path)
    errors: list[str] = []
    worker = _ChunkWorker("slow text", 0, 1, config)
    worker.error.connect(lambda message, _index, _total: errors.append(message))
    with patch("httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.post.side_effect = httpx.ReadTimeout(
            "slow"
        )
        worker.run()

    assert errors == ["Request timed out after 10 seconds"]


def test_non_audio_response_is_rejected(tmp_path):
    from speak_helper.speech_service import _ChunkWorker

    config = _make_config(tmp_path)
    errors: list[str] = []
    worker = _ChunkWorker("bad response", 0, 1, config)
    worker.error.connect(lambda message, _index, _total: errors.append(message))
    response = MagicMock(content=b'{"error": true}', headers={"content-type": "application/json"})
    response.raise_for_status = MagicMock()
    with patch("httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.post.return_value = response
        worker.run()

    assert errors and "unsupported content type" in errors[0]


@pytest.mark.parametrize(
    ("side_effect", "expected"),
    [
        (httpx.ConnectError("refused"), "Connection refused"),
        (
            httpx.HTTPStatusError(
                "server error",
                request=httpx.Request("POST", "http://local/v1/audio/speech"),
                response=httpx.Response(503),
            ),
            "HTTP 503",
        ),
    ],
)
def test_transport_errors_are_actionable(tmp_path, side_effect, expected):
    from speak_helper.speech_service import _ChunkWorker

    config = _make_config(tmp_path)
    errors: list[str] = []
    worker = _ChunkWorker("transport error", 0, 1, config)
    worker.error.connect(lambda message, _index, _total: errors.append(message))
    with patch("httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.post.side_effect = side_effect
        worker.run()

    assert errors and expected in errors[0]


def test_empty_audio_response_is_rejected(tmp_path):
    from speak_helper.speech_service import _ChunkWorker

    config = _make_config(tmp_path)
    errors: list[str] = []
    worker = _ChunkWorker("empty response", 0, 1, config)
    worker.error.connect(lambda message, _index, _total: errors.append(message))
    response = MagicMock(content=b"", headers={"content-type": "audio/mpeg"})
    response.raise_for_status = MagicMock()
    with patch("httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.post.return_value = response
        worker.run()

    assert errors == ["TTS server returned an empty audio response"]


def test_obsolete_temporary_chunk_is_removed(tmp_path):
    from speak_helper.speech_service import SpeechService

    path = tmp_path / "obsolete.mp3"
    path.write_bytes(b"audio")
    service = SpeechService(_make_config(tmp_path))
    service._generation = 1

    service._on_chunk_ready(0, str(path), 0, 1, True)

    assert not path.exists()


def test_failed_edge_synthesis_removes_partial_temporary_file(tmp_path):
    from speak_helper.speech_service import _ChunkWorker

    config = _make_config(tmp_path)
    config.backend = "edge"
    config.edge_voice = "en-US-AriaNeural"
    config.cache_enabled = False
    partial = tmp_path / "partial.mp3"
    partial.write_bytes(b"partial")
    worker = _ChunkWorker("hello", 0, 1, config)

    with (
        patch("speak_helper.speech_service._temporary_audio_path", return_value=partial),
        patch.object(worker, "_edge_save", AsyncMock(side_effect=RuntimeError("failed"))),
        pytest.raises(RuntimeError, match="failed"),
    ):
        worker._fetch_edge()

    assert not partial.exists()


def test_qwen_cache_separates_languages(tmp_path):
    from speak_helper.speech_service import _ChunkWorker

    config = _make_config(tmp_path)
    config.provider_preset = "qwen3_local"
    response = MagicMock(content=b"audio", headers={"content-type": "audio/mpeg"})
    response.raise_for_status = MagicMock()
    with patch("httpx.Client") as client_class:
        post = client_class.return_value.__enter__.return_value.post
        post.return_value = response
        english_path = _ChunkWorker("shared text", 0, 1, config)._fetch_openai()
        config.language = "fr"
        french_path = _ChunkWorker("shared text", 0, 1, config)._fetch_openai()

    assert english_path != french_path
    assert post.call_count == 2
    assert post.call_args.kwargs["json"]["language"] == "French"
