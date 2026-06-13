"""TTS 服务：分句 → 流水线请求 → 逐块返回音频
流程：
  text → split_sentences → [chunk1, chunk2, ...] → _PipelineWorker(QThread)
                                                      ↓ 每完成一块
                                               chunk_ready(path, idx, total)
                                                      ↓
                                               AudioPlayer.enqueue(path)  （边下边播）
"""
from __future__ import annotations

import asyncio
import hashlib
import re
import tempfile
from pathlib import Path
from typing import List

import httpx
from PySide6.QtCore import QObject, QThread, Signal

from .config import Config

# ── 分句工具 ──────────────────────────────────────────────────────────────────

# 句末标点（中英文）
_SENT_END = re.compile(r'(?<=[。！？…!?])\s*')
# 段落分隔
_PARA_SEP = re.compile(r'\n\s*\n')


def split_sentences(text: str) -> List[str]:
    """将文本拆分为句子列表"""
    parts: List[str] = []
    for para in _PARA_SEP.split(text):
        for sent in _SENT_END.split(para):
            s = sent.strip()
            if s:
                parts.append(s)
    return parts


def make_chunks(sentences: List[str], n: int) -> List[str]:
    """将句子列表每 n 句合并为一块"""
    if not sentences:
        return [" "]  # 空文本也给一个占位块
    chunks = []
    for i in range(0, len(sentences), n):
        chunk = "".join(sentences[i : i + n]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks or [sentences[0]]


# ── 单块 TTS Worker ───────────────────────────────────────────────────────────

class _ChunkWorker(QObject):
    """在独立线程中请求单块音频"""

    chunk_ready = Signal(str, int, int)   # (audio_path, chunk_idx, total)
    error       = Signal(str, int, int)   # (msg, chunk_idx, total)

    def __init__(
        self,
        chunk: str,
        idx: int,
        total: int,
        config: Config,
    ) -> None:
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
        if self.config.backend == "edge":
            return self._fetch_edge()
        return self._fetch_openai()

    # ── Edge-TTS 后端 ─────────────────────────────────────────────────────────

    def _fetch_edge(self) -> str:
        cfg = self.config
        voice = cfg.edge_voice
        # speed → edge-tts rate 字符串：1.2 → "+20%"
        rate_pct = int(round((cfg.speed - 1.0) * 100))
        rate_str = f"+{rate_pct}%" if rate_pct >= 0 else f"{rate_pct}%"

        cache_key = hashlib.sha1(
            f"edge|{self.chunk}|{voice}|{rate_str}".encode("utf-8", errors="replace")
        ).hexdigest()

        if cfg.cache_enabled:
            cache_file = cfg.cache_dir / f"{cache_key}.mp3"
            if cache_file.exists():
                return str(cache_file)

        out_path = (
            cfg.cache_dir / f"{cache_key}.mp3"
            if cfg.cache_enabled
            else Path(tempfile.mktemp(suffix=".mp3"))
        )
        # edge-tts 是异步库，在工作线程里用独立事件循环调用
        asyncio.run(self._edge_save(self.chunk, voice, rate_str, str(out_path)))

        if cfg.cache_enabled:
            self._evict_cache()
        return str(out_path)

    @staticmethod
    async def _edge_save(text: str, voice: str, rate: str, out_path: str) -> None:
        import edge_tts
        communicate = edge_tts.Communicate(text, voice, rate=rate)
        await communicate.save(out_path)

    # ── OpenAI 兼容后端 ───────────────────────────────────────────────────────

    def _fetch_openai(self) -> str:
        cfg = self.config
        cache_key = hashlib.sha1(
            f"{self.chunk}|{cfg.voice}|{cfg.model}|{cfg.speed}|{cfg.audio_format}"
            .encode("utf-8", errors="replace")
        ).hexdigest()

        if cfg.cache_enabled:
            cache_file = cfg.cache_dir / f"{cache_key}.{cfg.audio_format}"
            if cache_file.exists():
                return str(cache_file)

        headers = {
            "Authorization": f"Bearer {cfg.api_key}",
            "Content-Type": "application/json",
        }
        payload: dict = {
            "model": cfg.model,
            "input": self.chunk,
            "voice": cfg.voice,
            "speed": cfg.speed,
            "response_format": cfg.audio_format,
        }

        with httpx.Client(timeout=cfg.timeout_sec) as client:
            resp = client.post(
                f"{cfg.base_url.rstrip('/')}/audio/speech",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            audio_bytes = resp.content

        if cfg.cache_enabled:
            out_path = cfg.cache_dir / f"{cache_key}.{cfg.audio_format}"
            out_path.write_bytes(audio_bytes)
            self._evict_cache()
            return str(out_path)
        else:
            tmp = tempfile.NamedTemporaryFile(
                suffix=f".{cfg.audio_format}", delete=False
            )
            tmp.write(audio_bytes)
            tmp.close()
            return tmp.name

    def _evict_cache(self) -> None:
        cache_dir = self.config.cache_dir
        max_bytes = self.config.cache_max_mb * 1024 * 1024
        files = sorted(cache_dir.glob("*"), key=lambda p: p.stat().st_mtime)
        total = sum(p.stat().st_size for p in files)
        while total > max_bytes and files:
            oldest = files.pop(0)
            total -= oldest.stat().st_size
            try:
                oldest.unlink()
            except OSError:
                pass


# ── 流水线调度器（顺序请求所有块）────────────────────────────────────────────

class _PipelineWorker(QObject):
    """在独立线程中顺序请求所有分块，每块完成后立即发出信号（边下边播）"""

    chunk_ready = Signal(str, int, int)   # (path, idx, total)
    error       = Signal(str, int, int)
    all_done    = Signal()

    def __init__(self, chunks: List[str], config: Config) -> None:
        super().__init__()
        self._chunks = chunks
        self._config = config
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._chunks)
        for idx, chunk in enumerate(self._chunks):
            if self._cancelled:
                return
            worker = _ChunkWorker(chunk, idx, total, self._config)
            # 同步调用（在同一线程内执行，避免嵌套线程）
            try:
                path = worker._fetch()
            except Exception as exc:
                if not self._cancelled:
                    self.error.emit(str(exc), idx, total)
                return
            if self._cancelled:
                return
            self.chunk_ready.emit(path, idx, total)

        if not self._cancelled:
            self.all_done.emit()


# ── 对外接口 ──────────────────────────────────────────────────────────────────

class SpeechService(QObject):
    """分句、流水线 TTS 请求；每块音频就绪时发出 chunk_ready 信号"""

    started      = Signal()
    chunk_ready  = Signal(str, int, int)   # (path, chunk_idx, total_chunks)
    finished     = Signal()
    error        = Signal(str)

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._thread: QThread | None = None
        self._worker: _PipelineWorker | None = None

    def speak(self, text: str) -> None:
        self._cancel_current()

        sentences = split_sentences(text)
        chunks = make_chunks(sentences, self._config.sentences_per_chunk)

        self._thread = QThread(self)
        self._worker = _PipelineWorker(chunks, self._config)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.chunk_ready.connect(self._on_chunk_ready)
        self._worker.error.connect(self._on_error)
        self._worker.all_done.connect(self._on_all_done)
        self._worker.all_done.connect(self._thread.quit)
        self._worker.error.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)

        self.started.emit()
        self._thread.start()

    def stop(self) -> None:
        self._cancel_current()
        self.finished.emit()

    # ── private ───────────────────────────────────────────────────────────────

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None

    def _cancel_current(self) -> None:
        if self._worker:
            self._worker.cancel()
        if self._thread is not None:
            try:
                if self._thread.isRunning():
                    self._thread.quit()
                    self._thread.wait(500)
            except RuntimeError:
                pass
        self._thread = None
        self._worker = None

    def _on_chunk_ready(self, path: str, idx: int, total: int) -> None:
        self.chunk_ready.emit(path, idx, total)

    def _on_all_done(self) -> None:
        pass   # finished 由 AudioPlayer 播完最后一块后发出

    def _on_error(self, msg: str, idx: int, _total: int) -> None:
        self.finished.emit()
        self.error.emit(f"第 {idx + 1} 块失败：{msg}")
