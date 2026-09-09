"""Chunked Edge and OpenAI-compatible text-to-speech pipeline."""

from __future__ import annotations

import asyncio
import contextlib
import hashlib
import os
import re
import tempfile
from pathlib import Path

import httpx
from PySide6.QtCore import QObject, QThread, Signal

from .config import Config

_SENT_END = re.compile(r"(?<=[.!?…。！？])\s+")  # noqa: RUF001
_PARA_SEP = re.compile(r"\n\s*\n")
_SUPPORTED_AUDIO_FORMATS = {"mp3", "wav", "opus", "aac", "flac", "pcm"}


def split_sentences(text: str) -> list[str]:
    """Split text at common English, French, and CJK sentence boundaries."""
    parts: list[str] = []
    for paragraph in _PARA_SEP.split(text):
        parts.extend(
            sentence.strip() for sentence in _SENT_END.split(paragraph) if sentence.strip()
        )
    return parts


def make_chunks(sentences: list[str], size: int) -> list[str]:
    """Group sentences into low-latency synthesis requests."""
    if not sentences:
        return [" "]
    chunks = [
        " ".join(sentences[index : index + size]).strip()
        for index in range(0, len(sentences), size)
    ]
    return [chunk for chunk in chunks if chunk] or [sentences[0]]


class _ChunkWorker(QObject):
    """Fetch one audio chunk from the selected backend."""

    chunk_ready = Signal(str, int, int)
    error = Signal(str, int, int)

    def __init__(self, chunk: str, idx: int, total: int, config: Config) -> None:
        super().__init__()
        self.chunk = chunk
        self.idx = idx
        self.total = total
        self.config = config
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        if self._cancelled:
            return
        try:
            path = self._fetch()
            if not self._cancelled:
                self.chunk_ready.emit(path, self.idx, self.total)
        except Exception as exc:
            if not self._cancelled:
                self.error.emit(str(exc), self.idx, self.total)

    def _fetch(self) -> str:
        return self._fetch_edge() if self.config.backend == "edge" else self._fetch_openai()

    def _fetch_edge(self) -> str:
        config = self.config
        rate_percent = round((config.speed - 1.0) * 100)
        rate = f"+{rate_percent}%" if rate_percent >= 0 else f"{rate_percent}%"
        cache_key = hashlib.sha1(
            f"edge|{self.chunk}|{config.edge_voice}|{rate}".encode("utf-8", errors="replace")
        ).hexdigest()
        cache_file = config.cache_dir / f"{cache_key}.mp3"
        if config.cache_enabled and cache_file.exists():
            return str(cache_file)
        output = cache_file if config.cache_enabled else _temporary_audio_path("mp3")
        asyncio.run(self._edge_save(self.chunk, config.edge_voice, rate, str(output)))
        if not output.exists() or output.stat().st_size == 0:
            raise RuntimeError("Edge TTS returned an empty audio response")
        if config.cache_enabled:
            self._evict_cache()
        return str(output)

    @staticmethod
    async def _edge_save(text: str, voice: str, rate: str, output: str) -> None:
        import edge_tts

        await edge_tts.Communicate(text, voice, rate=rate).save(output)

    def _fetch_openai(self) -> str:
        config = self.config
        if config.audio_format not in _SUPPORTED_AUDIO_FORMATS:
            raise ValueError(f"Unsupported audio format: {config.audio_format}")
        cache_key = hashlib.sha1(
            (
                f"{config.base_url}|{self.chunk}|{config.voice}|{config.model}|"
                f"{config.speed}|{config.audio_format}"
            ).encode("utf-8", errors="replace")
        ).hexdigest()
        cache_file = config.cache_dir / f"{cache_key}.{config.audio_format}"
        if config.cache_enabled and cache_file.exists():
            return str(cache_file)

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
        endpoint = f"{config.base_url.rstrip('/')}/audio/speech"
        try:
            with httpx.Client(timeout=config.timeout_sec) as client:
                response = client.post(
                    endpoint,
                    headers=headers,
                    json={
                        "model": config.model,
                        "input": self.chunk,
                        "voice": config.voice,
                        "speed": config.speed,
                        "response_format": config.audio_format,
                    },
                )
                response.raise_for_status()
        except httpx.ConnectError as exc:
            raise RuntimeError(f"Connection refused by {endpoint}") from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(f"Request timed out after {config.timeout_sec} seconds") from exc
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(f"TTS server returned HTTP {exc.response.status_code}") from exc

        content_type = response.headers.get("content-type", "")
        if content_type and not (
            content_type.startswith("audio/") or content_type == "application/octet-stream"
        ):
            raise RuntimeError(f"TTS server returned unsupported content type: {content_type}")
        if not response.content:
            raise RuntimeError("TTS server returned an empty audio response")
        output = cache_file if config.cache_enabled else _temporary_audio_path(config.audio_format)
        output.write_bytes(response.content)
        if config.cache_enabled:
            self._evict_cache()
        return str(output)

    def _evict_cache(self) -> None:
        files = sorted(self.config.cache_dir.glob("*"), key=lambda path: path.stat().st_mtime)
        total = sum(path.stat().st_size for path in files)
        maximum = self.config.cache_max_mb * 1024 * 1024
        while total > maximum and files:
            oldest = files.pop(0)
            total -= oldest.stat().st_size
            with contextlib.suppress(OSError):
                oldest.unlink()


def _temporary_audio_path(extension: str) -> Path:
    handle, path = tempfile.mkstemp(suffix=f".{extension}")
    os.close(handle)
    return Path(path)


class _PipelineWorker(QObject):
    """Fetch chunks sequentially and emit each as soon as it is ready."""

    chunk_ready = Signal(str, int, int)
    error = Signal(str, int, int)
    all_done = Signal()
    completed = Signal()

    def __init__(self, chunks: list[str], config: Config) -> None:
        super().__init__()
        self._chunks = chunks
        self._config = config
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            total = len(self._chunks)
            for index, chunk in enumerate(self._chunks):
                if self._cancelled:
                    return
                worker = _ChunkWorker(chunk, index, total, self._config)
                try:
                    path = worker._fetch()
                except Exception as exc:
                    if not self._cancelled:
                        self.error.emit(str(exc), index, total)
                    return
                if self._cancelled:
                    return
                self.chunk_ready.emit(path, index, total)
            if not self._cancelled:
                self.all_done.emit()
        finally:
            self.completed.emit()


class SpeechService(QObject):
    """Own cancellable, chunked synthesis jobs without blocking the UI thread."""

    started = Signal()
    chunk_ready = Signal(str, int, int)
    finished = Signal()
    error = Signal(str)

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._generation = 0
        self._jobs: dict[int, tuple[QThread, _PipelineWorker]] = {}

    def speak(self, text: str) -> None:
        self._cancel_current()
        generation = self._generation
        chunks = make_chunks(split_sentences(text), self._config.sentences_per_chunk)
        thread = QThread(self)
        worker = _PipelineWorker(chunks, self._config)
        worker.moveToThread(thread)
        self._jobs[generation] = (thread, worker)
        thread.started.connect(worker.run)
        worker.chunk_ready.connect(
            lambda path, index, total, job=generation: self._on_chunk_ready(job, path, index, total)
        )
        worker.error.connect(
            lambda message, index, total, job=generation: self._on_error(job, message, index, total)
        )
        worker.completed.connect(thread.quit)
        worker.completed.connect(worker.deleteLater)
        thread.finished.connect(lambda job=generation: self._on_thread_finished(job))
        thread.finished.connect(thread.deleteLater)
        self.started.emit()
        thread.start()

    def stop(self) -> None:
        self._cancel_current()
        self.finished.emit()

    def shutdown(self) -> None:
        """Cancel outstanding work and wait for network calls to leave their threads."""
        self._cancel_current()
        maximum_wait = (self._config.timeout_sec + 1) * 1_000
        for thread, _worker in tuple(self._jobs.values()):
            if thread.isRunning():
                thread.quit()
                thread.wait(maximum_wait)

    def _cancel_current(self) -> None:
        self._generation += 1
        for thread, worker in self._jobs.values():
            worker.cancel()
            thread.requestInterruption()

    def _on_thread_finished(self, generation: int) -> None:
        job = self._jobs.pop(generation, None)
        del job

    def _on_chunk_ready(self, generation: int, path: str, index: int, total: int) -> None:
        if generation == self._generation:
            self.chunk_ready.emit(path, index, total)

    def _on_error(self, generation: int, message: str, index: int, _total: int) -> None:
        if generation == self._generation:
            self.finished.emit()
            self.error.emit(f"Chunk {index + 1} failed: {message}")
