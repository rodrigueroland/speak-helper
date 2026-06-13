# -*- coding: utf-8 -*-
"""音频播放器：支持顺序播放队列，配合分块 TTS 实现边下边播

修复说明：
  原版使用 playbackStateChanged → StoppedState 触发下一块，
  但 setSource() 切换音源时也会触发 StoppedState，导致队列被
  提前推进——新文件 play() 还没执行就被跳过，表现为有状态无声音。
  修复：改用 mediaStatusChanged → EndOfMedia 触发下一块。
"""
from __future__ import annotations

import logging
from collections import deque

from PySide6.QtCore import QObject, QTimer, QUrl, Signal
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

logger = logging.getLogger(__name__)


class AudioPlayer(QObject):
    playback_started  = Signal()          # 第一块开始播放
    chunk_started     = Signal(int, int)  # (chunk_idx, total) 每块开始
    playback_finished = Signal()          # 整个队列播完
    error             = Signal(str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio_output = QAudioOutput(self)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(1.0)

        self._queue: deque[tuple[str, int, int]] = deque()  # (path, idx, total)
        self._playing = False
        self._first_chunk = True

        # 用 EndOfMedia 触发下一块，避免 setSource 时误触 StoppedState
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_error)
        self._player.playbackStateChanged.connect(self._on_playback_state)

    # ── public API ────────────────────────────────────────────────────────────

    def enqueue(self, path: str, chunk_idx: int, total: int) -> None:
        """将一个音频块加入队列，如果当前空闲则立即开始播放"""
        self._queue.append((path, chunk_idx, total))
        logger.debug("enqueue idx=%d/%d path=%s queue_len=%d",
                     chunk_idx, total, path, len(self._queue))
        if not self._playing:
            self._play_next()

    def stop(self) -> None:
        """停止当前播放并清空队列"""
        self._queue.clear()
        self._playing = False
        self._first_chunk = True
        self._player.stop()

    def set_volume(self, volume: float) -> None:
        self._audio_output.setVolume(max(0.0, min(1.0, volume)))

    def reset(self) -> None:
        """开始新一轮朗读前重置状态"""
        self._queue.clear()
        self._playing = False
        self._first_chunk = True

    # ── private ───────────────────────────────────────────────────────────────

    def _play_next(self) -> None:
        if not self._queue:
            self._playing = False
            logger.debug("queue empty → playback_finished")
            self.playback_finished.emit()
            return

        path, idx, total = self._queue.popleft()
        logger.debug("play_next idx=%d/%d path=%s", idx, total, path)

        if self._first_chunk:
            self._first_chunk = False
            self.playback_started.emit()

        self.chunk_started.emit(idx, total)

        # 先设置 playing=True，再 setSource + play，
        # 避免 setSource 触发的状态回调认为"空闲"而重入
        self._playing = True
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        logger.debug("mediaStatus=%s playing=%s", status, self._playing)
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # 正常播完一块，继续下一块
            self._play_next()
        elif status == QMediaPlayer.MediaStatus.InvalidMedia:
            logger.warning("InvalidMedia, skipping chunk")
            self.error.emit("音频文件无效，已跳过")
            self._play_next()

    def _on_playback_state(self, state: QMediaPlayer.PlaybackState) -> None:
        # 仅用于日志，不再用于触发 _play_next
        logger.debug("playbackState=%s", state)

    def _on_error(self, error: QMediaPlayer.Error, error_string: str) -> None:
        if error != QMediaPlayer.Error.NoError:
            logger.error("QMediaPlayer error: %s", error_string)
            self.error.emit(error_string)
            # 出错时跳过当前块，继续播下一块
            self._playing = False
            self._play_next()
