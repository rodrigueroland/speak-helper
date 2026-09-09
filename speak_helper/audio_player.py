"""Sequential audio playback with explicit pause, resume, and replacement."""

from __future__ import annotations

import logging
from collections import deque
from contextlib import suppress
from pathlib import Path

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

logger = logging.getLogger(__name__)


class AudioPlayer(QObject):
    playback_started = Signal()
    playback_paused = Signal()
    playback_resumed = Signal()
    playback_stopped = Signal()
    chunk_started = Signal(int, int)
    playback_finished = Signal()
    error = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)

        self._queue: deque[tuple[str, int, int, bool]] = deque()
        self._current_temporary: Path | None = None
        self._playing = False
        self._paused = False
        self._started_emitted = False

        # EndOfMedia avoids treating the StoppedState emitted by setSource as completion.
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_error)
        self._player.playbackStateChanged.connect(self._on_playback_state)

    # ── public API ────────────────────────────────────────────────────────────

    def enqueue(self, path: str, chunk_idx: int, total: int, temporary: bool = False) -> None:
        """Enqueue a synthesized chunk and start immediately when idle."""
        self._queue.append((path, chunk_idx, total, temporary))
        logger.debug(
            "enqueue idx=%d/%d path=%s queue_len=%d", chunk_idx, total, path, len(self._queue)
        )
        if not self._playing:
            self._play_next()

    def stop(self) -> None:
        """Stop immediately and discard obsolete queued speech."""
        was_active = self._playing or self._paused or bool(self._queue)
        self._discard_queue()
        self._playing = False
        self._paused = False
        self._started_emitted = False
        self._player.stop()
        self._player.setSource(QUrl())
        self._discard_current()
        if was_active:
            self.playback_stopped.emit()

    def pause(self) -> None:
        if self._playing and not self._paused:
            self._player.pause()

    def resume(self) -> None:
        if self._paused:
            self._player.play()

    def toggle_pause(self) -> bool:
        if self._paused:
            self.resume()
        else:
            self.pause()
        return self._paused

    @property
    def state(self) -> str:
        if self._paused:
            return "paused"
        return "speaking" if self._playing else "idle"

    def set_volume(self, volume: float) -> None:
        self._audio_output.setVolume(max(0.0, min(1.0, volume)))

    def reset(self) -> None:
        """Replace current playback with a new manual reading."""
        self._discard_queue()
        self._playing = False
        self._paused = False
        self._started_emitted = False
        self._player.stop()
        self._player.setSource(QUrl())
        self._discard_current()

    # ── private ───────────────────────────────────────────────────────────────

    def _play_next(self) -> None:
        self._player.setSource(QUrl())
        self._discard_current()
        if not self._queue:
            self._playing = False
            logger.debug("queue empty → playback_finished")
            self.playback_finished.emit()
            return

        path, idx, total, temporary = self._queue.popleft()
        logger.debug("play_next idx=%d/%d path=%s", idx, total, path)

        self.chunk_started.emit(idx, total)

        # Mark playback active before setSource, whose callbacks may run synchronously.
        self._playing = True
        self._current_temporary = Path(path) if temporary else None
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def _discard_current(self) -> None:
        path = self._current_temporary
        self._current_temporary = None
        if path is not None:
            with suppress(OSError):
                path.unlink()

    def _discard_queue(self) -> None:
        while self._queue:
            path, _idx, _total, temporary = self._queue.popleft()
            if temporary:
                with suppress(OSError):
                    Path(path).unlink()

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        logger.debug("mediaStatus=%s playing=%s", status, self._playing)
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self._play_next()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            logger.warning("InvalidMedia, skipping chunk")
            self.error.emit("audio_invalid")
            self._play_next()

    def _on_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        logger.debug("playbackState=%s", state)
        if state == QMediaPlayer.PlaybackState.PlayingState:
            was_paused = self._paused
            self._playing = True
            self._paused = False
            if not self._started_emitted:
                self._started_emitted = True
                self.playback_started.emit()
            elif was_paused:
                self.playback_resumed.emit()
        elif state == QMediaPlayer.PlaybackState.PausedState:
            self._playing = True
            if not self._paused:
                self._paused = True
                self.playback_paused.emit()

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        if error != QMediaPlayer.Error.NoError:
            logger.error("QMediaPlayer error: %s", error_string)
            self.error.emit(error_string)
            self._playing = False
            self._play_next()
