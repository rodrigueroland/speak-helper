"""SpeechService 单元测试（mock httpx）"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.fixture(autouse=True)
def qt_app():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_config(tmp_path: Path):
    cfg = MagicMock()
    cfg.backend = "openai"
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
    from speak_helper.speech_service import _ChunkWorker
    import hashlib

    text = "hello"
    voice = "nova"
    model = "tts-1"
    speed = 1.2
    fmt = "mp3"
    key = hashlib.sha1(f"{text}|{voice}|{model}|{speed}|{fmt}".encode()).hexdigest()
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
