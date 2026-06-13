# -*- coding: utf-8 -*-
"""
OCR 服务：调用 OpenAI 兼容的 Vision API（PaddleOCR-VL-1.5 等）
识别剪贴板图片中的文字，结果写入日志文件方便调试。

使用与 TTS 相同的 base_url / api_key，额外维护 ocr.model 字段。
"""
from __future__ import annotations

import base64
import io
import logging
from datetime import datetime
from pathlib import Path

import httpx
from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QImage

from .config import Config

# ── 日志 ──────────────────────────────────────────────────────────────────────

def _get_log_path() -> Path:
    from platformdirs import user_config_dir
    log_dir = Path(user_config_dir("speak_helper"))
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "ocr.log"


def _write_ocr_log(model: str, result: str, error: str = "") -> None:
    """将 OCR 结果追加写入 ocr.log，方便测试验证。"""
    try:
        log_path = _get_log_path()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sep = "-" * 60
        lines = [
            f"\n{sep}",
            f"[{ts}]  model: {model}",
        ]
        if error:
            lines.append(f"ERROR: {error}")
        else:
            lines.append("RESULT:")
            lines.append(result)
        lines.append(sep)
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    except Exception:
        pass  # 日志写失败不影响主流程


# ── 提示词 ────────────────────────────────────────────────────────────────────

_OCR_PROMPT = (
    "请提取图片中所有可见的文字，按照从上到下、从左到右的顺序输出。"
    "只输出文字内容本身，不要添加任何解释、标点修改或格式标注。"
    "如果图片中没有文字，请只回复：[no text]"
)

# ── 图片转换 ──────────────────────────────────────────────────────────────────

def _qimage_to_jpeg_b64(qimg: QImage, quality: int = 85) -> str:
    """将 QImage 转为 JPEG base64 字符串（减小传输体积）。"""
    from PIL import Image

    rgb = qimg.convertToFormat(QImage.Format.Format_RGB888)
    w, h = rgb.width(), rgb.height()
    pil_img = Image.frombytes("RGB", (w, h), bytes(rgb.bits()))

    # 长边超过 2048px 时缩小，避免 API 拒绝或超时
    max_side = 2048
    if max(w, h) > max_side:
        ratio = max_side / max(w, h)
        pil_img = pil_img.resize(
            (int(w * ratio), int(h * ratio)),
            Image.Resampling.LANCZOS,
        )

    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode()


# ── 工作线程 ──────────────────────────────────────────────────────────────────

class _OcrWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

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
            b64 = _qimage_to_jpeg_b64(self._qimage, self._quality)
            text = self._call_api(b64)
            cleaned = text.strip() if text else ""
            if cleaned.lower() in ("[no text]", "no text", ""):
                msg = "图片中未识别到文字"
                _write_ocr_log(self._model, "", error=msg)
                self.error.emit(msg)
            else:
                _write_ocr_log(self._model, cleaned)
                self.finished.emit(cleaned)
        except Exception as exc:
            msg = f"OCR 失败：{exc}"
            _write_ocr_log(self._model, "", error=msg)
            self.error.emit(msg)

    def _call_api(self, b64: str) -> str:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                        },
                        {"type": "text", "text": _OCR_PROMPT},
                    ],
                }
            ],
            "max_tokens": 4096,
            "temperature": 0,
        }
        url = f"{self._base_url}/chat/completions"
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]


# ── 公共服务 ──────────────────────────────────────────────────────────────────

class OcrService(QObject):
    """从剪贴板图片调用 Vision API 提取文字，识别完成后发出 text_ready 信号。"""

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

    @property
    def log_path(self) -> Path:
        return _get_log_path()

    def recognize_clipboard_image(self, qimage: QImage) -> None:
        """异步识别 QImage，结果通过 text_ready 发出。"""
        if not self.enabled:
            return
        if not self._config.api_key:
            self.error.emit("OCR 需要 API Key，请在设置中填写")
            return
        if self._worker and self._worker.isRunning():
            return

        self._worker = _OcrWorker(
            qimage=qimage,
            base_url=self._config.base_url,
            api_key=self._config.api_key,
            model=self._config.ocr_model,
            quality=self._config.ocr_image_quality,
        )
        self._worker.finished.connect(self._on_done)
        self._worker.finished.connect(lambda _: self.finished.emit())
        self._worker.error.connect(self.error)
        self._worker.error.connect(lambda _: self.finished.emit())
        self.started.emit()
        self._worker.start()

    def _on_done(self, text: str) -> None:
        self.text_ready.emit(text)
