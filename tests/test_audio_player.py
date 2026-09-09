"""Audio queue state-transition tests."""

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer

from speak_helper.audio_player import AudioPlayer


class FakeMediaPlayer:
    def __init__(self) -> None:
        self.source = QUrl()
        self.calls: list[str] = []

    def setSource(self, source: QUrl) -> None:
        self.source = source

    def play(self) -> None:
        self.calls.append("play")

    def pause(self) -> None:
        self.calls.append("pause")

    def stop(self) -> None:
        self.calls.append("stop")


def test_pause_resume_and_stop_follow_media_state(qtbot):
    player = AudioPlayer()
    media = FakeMediaPlayer()
    player._player = media
    started: list[bool] = []
    paused: list[bool] = []
    resumed: list[bool] = []
    stopped: list[bool] = []
    player.playback_started.connect(lambda: started.append(True))
    player.playback_paused.connect(lambda: paused.append(True))
    player.playback_resumed.connect(lambda: resumed.append(True))
    player.playback_stopped.connect(lambda: stopped.append(True))

    player.enqueue("first.mp3", 0, 1)
    player._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
    assert player.state == "speaking"
    assert started == [True]
    player.pause()
    player._on_playback_state(QMediaPlayer.PlaybackState.PausedState)
    assert player.state == "paused"
    assert paused == [True]
    player.resume()
    player._on_playback_state(QMediaPlayer.PlaybackState.PlayingState)
    assert player.state == "speaking"
    assert resumed == [True]
    player.stop()
    assert player.state == "idle"
    assert stopped == [True]
    assert media.source.isEmpty()


def test_reset_replaces_obsolete_queue(qtbot):
    player = AudioPlayer()
    media = FakeMediaPlayer()
    player._player = media
    player.enqueue("current.mp3", 0, 2)
    player.enqueue("obsolete.mp3", 1, 2)

    player.reset()
    player.enqueue("replacement.mp3", 0, 1)

    assert media.source.toLocalFile().endswith("replacement.mp3")
    assert len(player._queue) == 0
