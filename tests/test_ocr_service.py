"""OCR transport, response, and cancellation tests."""

import base64
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtGui import QColor, QImage

from speak_helper.ocr_service import _OcrWorker, _qimage_to_jpeg_b64


def _worker(api_key: str = "") -> _OcrWorker:
    image = QImage(8, 8, QImage.Format.Format_RGB32)
    image.fill(QColor("white"))
    return _OcrWorker(
        image,
        "http://127.0.0.1:8000/v1",
        api_key,
        "vision-model",
        85,
        3,
    )


def test_qimage_conversion_produces_jpeg() -> None:
    encoded = _qimage_to_jpeg_b64(_worker()._qimage)
    assert base64.b64decode(encoded).startswith(b"\xff\xd8")


def test_ocr_request_omits_empty_authorization_and_extracts_text() -> None:
    response = MagicMock()
    response.json.return_value = {"choices": [{"message": {"content": "Bonjour"}}]}
    with patch("speak_helper.ocr_service.httpx.Client") as client_class:
        client = client_class.return_value.__enter__.return_value
        client.post.return_value = response
        result = _worker()._call_api("encoded")

    headers = client.post.call_args.kwargs["headers"]
    assert "Authorization" not in headers
    assert result == "Bonjour"


def test_ocr_request_adds_nonempty_authorization() -> None:
    response = MagicMock()
    response.json.return_value = {"choices": [{"message": {"content": "Text"}}]}
    with patch("speak_helper.ocr_service.httpx.Client") as client_class:
        client = client_class.return_value.__enter__.return_value
        client.post.return_value = response
        _worker("test-key")._call_api("encoded")

    assert client.post.call_args.kwargs["headers"]["Authorization"] == "Bearer test-key"


def test_invalid_ocr_response_is_actionable() -> None:
    response = MagicMock()
    response.json.return_value = {"unexpected": True}
    with patch("speak_helper.ocr_service.httpx.Client") as client_class:
        client_class.return_value.__enter__.return_value.post.return_value = response
        with pytest.raises(RuntimeError, match="invalid response"):
            _worker()._call_api("encoded")


def test_ocr_worker_reports_no_text() -> None:
    worker = _worker()
    errors: list[str] = []
    worker.failed.connect(errors.append)
    with patch.object(worker, "_call_api", return_value="[no text]"):
        worker.run()
    assert errors == ["ocr_no_text"]


def test_interrupted_ocr_worker_does_not_call_provider() -> None:
    worker = _worker()
    with (
        patch.object(worker, "isInterruptionRequested", return_value=True),
        patch.object(worker, "_call_api") as call_api,
    ):
        worker.run()
    call_api.assert_not_called()
