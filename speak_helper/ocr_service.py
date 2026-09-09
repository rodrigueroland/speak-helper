"""Optional OCR service backed by an OpenAI-compatible vision endpoint."""

from __future__ import annotations

import base64
import io
import logging

import httpx
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QImage

from .config import Config

logger = logging.getLogger(__name__)

_OCR_PROMPT = (
    "Extract all visible text in reading order. Return only the extracted text, "
    "without commentary or formatting changes. Return [no text] if none is visible."
)


def _qimage_to_jpeg_b64(qimage: QImage, quality: int = 85) -> str:
    """Convert a QImage to a reasonably sized base64-encoded JPEG."""
    from PIL import Image

    rgb = qimage.convertToFormat(QImage.Format.Format_RGB888)
    width, height = rgb.width(), rgb.height()
    image = Image.frombytes("RGB", (width, height), bytes(rgb.bits()))
    max_side = 2048
    if max(width, height) > max_side:
        ratio = max_side / max(width, height)
        image = image.resize((int(width * ratio), int(height * ratio)), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


class _OcrWorker(QThread):
    result_ready = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        qimage: QImage,
        base_url: str,
        api_key: str,
        model: str,
        quality: int,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._qimage = qimage
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._quality = quality

    def run(self) -> None:
        try:
            text = self._call_api(_qimage_to_jpeg_b64(self._qimage, self._quality)).strip()
            if text.lower() in {"", "[no text]", "no text"}:
                logger.info("ocr_completed model=%s text_length=0", self._model)
                self.failed.emit("ocr_no_text")
                return
            logger.info("ocr_completed model=%s text_length=%d", self._model, len(text))
            self.result_ready.emit(text)
        except Exception as exc:
            logger.exception("ocr_failed model=%s", self._model)
            self.failed.emit(str(exc))

    def _call_api(self, encoded_image: str) -> str:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"},
                        },
                        {"type": "text", "text": _OCR_PROMPT},
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0,
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self._base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            data = response.json()
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("The OCR server returned an invalid response") from exc


class OcrService(QObject):
    """Run OCR only when enabled and report results through Qt signals."""

    text_ready = Signal(str)
    error = Signal(str)
    started = Signal()
    finished = Signal()

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._worker: _OcrWorker | None = None

    @property
    def enabled(self) -> bool:
        return self._config.ocr_enabled

    def recognize_clipboard_image(self, qimage: QImage) -> None:
        if not self.enabled or (self._worker and self._worker.isRunning()):
            return
        self._worker = _OcrWorker(
            qimage=qimage,
            base_url=self._config.base_url,
            api_key=self._config.api_key,
            model=self._config.ocr_model,
            quality=self._config.ocr_image_quality,
        )
        self._worker.result_ready.connect(self._on_done)
        self._worker.failed.connect(self.error)
        self._worker.finished.connect(self._on_finished)
        self.started.emit()
        self._worker.start()

    def stop(self) -> None:
        worker = self._worker
        if worker and worker.isRunning():
            worker.requestInterruption()
            worker.quit()
            worker.wait(500)

    def _on_done(self, text: str) -> None:
        self.text_ready.emit(text)

    def _on_finished(self) -> None:
        self._worker = None
        self.finished.emit()
