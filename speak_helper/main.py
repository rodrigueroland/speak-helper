"""Application composition root and lifecycle."""

from __future__ import annotations

import ctypes
import logging
import sys

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from . import __version__
from .audio_player import AudioPlayer
from .clipboard_watcher import ClipboardWatcher
from .config import Config
from .error_messages import localize_audio_error, localize_ocr_error, localize_speech_error
from .hotkey_service import ACTION_READ, HotkeyService
from .i18n import Translator
from .logging_config import configure_logging
from .ocr_service import OcrService
from .selection_capture import SelectionCaptureService
from .speech_service import SpeechService
from .text_filter import TextFilter
from .text_normalizer import NormalizationOptions, normalize_for_speech
from .ui.floating_dock import FloatingDock
from .ui.prompt_bubble import PromptBubble
from .ui.settings_dialog import SettingsDialog
from .ui.theme import stylesheet_for_theme
from .ui.tray_icon import TrayIcon

logger = logging.getLogger(__name__)
_MUTEX_NAME = "Global\\SpeakHelper_SingleInstance_Mutex"
_mutex_handle: int | None = None


def _acquire_single_instance() -> bool:
    """Acquire the Windows process mutex; other platforms currently pass through."""
    global _mutex_handle
    if sys.platform != "win32":
        return True
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
    kernel32.CloseHandle.restype = wintypes.BOOL
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, True, _MUTEX_NAME)
    if not handle:
        logger.error("single_instance_mutex_failed code=%d", ctypes.get_last_error())
        return True
    if ctypes.get_last_error() == 183:
        kernel32.CloseHandle(handle)
        return False
    _mutex_handle = int(handle)
    return True


def _release_single_instance() -> None:
    global _mutex_handle
    if sys.platform == "win32" and _mutex_handle is not None:
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.ReleaseMutex.argtypes = (wintypes.HANDLE,)
        kernel32.ReleaseMutex.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = wintypes.HANDLE(_mutex_handle)
        kernel32.ReleaseMutex(handle)
        kernel32.CloseHandle(handle)
        _mutex_handle = None


class SpeakHelperApp:
    """Coordinate use cases while keeping UI and infrastructure focused."""

    def __init__(self, application: QApplication) -> None:
        self._application = application
        self._last_text = ""
        self._pending_image: QImage | None = None
        self._config = Config()
        self._application.setStyleSheet(stylesheet_for_theme(self._config.theme, self._application))
        self._log_path = configure_logging(self._config.log_dir)
        self._translator = Translator(self._config)
        self._speech = SpeechService(self._config)
        self._player = AudioPlayer()
        self._text_filter = TextFilter(self._config)
        self._clipboard_watcher = ClipboardWatcher(self._config)
        self._selection_capture = SelectionCaptureService(self._config)
        self._hotkeys = HotkeyService(self._config)
        self._ocr = OcrService(self._config)
        self._dock = FloatingDock(self._config, self._translator)
        self._bubble = PromptBubble(self._config, self._translator)
        self._tray = TrayIcon(self._config, self._translator)
        self._settings_dialog: SettingsDialog | None = None
        self._shutting_down = False
        self._connect_signals()
        self._apply_clipboard_mode()
        self._hotkeys.start()

    def _connect_signals(self) -> None:
        self._clipboard_watcher.text_changed.connect(self._text_filter.feed)
        self._text_filter.text_accepted.connect(self._on_clipboard_text)
        self._clipboard_watcher.image_changed.connect(self._on_clipboard_image)
        self._selection_capture.capture_started.connect(
            lambda: self._clipboard_watcher.set_suppressed(True)
        )
        self._selection_capture.capture_finished.connect(
            lambda: self._clipboard_watcher.set_suppressed(False)
        )
        self._selection_capture.text_ready.connect(self._speak)
        self._selection_capture.error.connect(self._on_capture_error)

        self._hotkeys.read_requested.connect(self._selection_capture.capture)
        self._hotkeys.stop_requested.connect(self._stop)
        self._hotkeys.pause_requested.connect(self._toggle_playback_pause)
        self._hotkeys.replay_requested.connect(self._replay_last)
        self._hotkeys.registration_changed.connect(self._on_hotkey_registration)
        self._hotkeys.error.connect(self._on_hotkey_error)

        self._bubble.confirmed.connect(self._speak)
        self._bubble.image_confirmed.connect(self._start_ocr)
        self._ocr.text_ready.connect(self._speak)
        self._ocr.started.connect(lambda: self._set_state("speaking"))
        self._ocr.error.connect(self._on_ocr_error)

        self._speech.started.connect(self._player.reset)
        self._speech.started.connect(lambda: self._set_state("speaking"))
        self._speech.chunk_ready.connect(self._player.enqueue)
        self._speech.error.connect(self._on_speech_error)
        self._player.playback_started.connect(lambda: logger.info("playback_started"))
        self._player.playback_paused.connect(lambda: self._set_state("paused"))
        self._player.playback_resumed.connect(lambda: self._set_state("speaking"))
        self._player.playback_finished.connect(self._on_playback_finished)
        self._player.playback_stopped.connect(lambda: logger.info("playback_stopped"))
        self._player.error.connect(self._on_player_error)

        self._dock.clicked.connect(self._toggle_playback_pause)
        self._dock.double_clicked.connect(self._replay_last)
        self._dock.right_clicked.connect(self._show_dock_menu)
        self._tray.read_requested.connect(self._selection_capture.capture)
        self._tray.pause_requested.connect(self._toggle_playback_pause)
        self._tray.stop_requested.connect(self._stop)
        self._tray.replay_requested.connect(self._replay_last)
        self._tray.mode_changed.connect(self._set_mode)
        self._tray.clipboard_toggled.connect(self._set_clipboard_monitoring)
        self._tray.hotkey_toggled.connect(self._set_hotkeys_enabled)
        self._tray.settings_requested.connect(self._show_settings)
        self._tray.about_requested.connect(self._show_about)
        self._tray.quit_requested.connect(self.quit)

    def _normalization_options(self) -> NormalizationOptions:
        return NormalizationOptions(
            strip_markdown_markers=bool(
                self._config.get("preprocessing", "strip_markdown_markers", default=True)
            ),
            preserve_code=bool(self._config.get("preprocessing", "preserve_code", default=True)),
            url_mode=str(self._config.get("preprocessing", "url_mode", default="keep")),
        )

    def _speak(self, text: str) -> None:
        normalized = normalize_for_speech(text, self._normalization_options())
        if not normalized:
            return
        self._last_text = normalized
        self._text_filter.reset_dedup()
        self._player.stop()
        logger.info(
            "tts_request_started length=%d backend=%s", len(normalized), self._config.backend
        )
        self._speech.speak(normalized)

    def _on_clipboard_text(self, text: str) -> None:
        if self._config.mode == "ask":
            self._bubble.show_for_text(text, self._dock)
        elif self._config.mode == "auto":
            self._speak(text)

    def _on_clipboard_image(self, image: QImage) -> None:
        if not self._config.ocr_enabled or self._config.mode == "manual":
            return
        self._pending_image = image
        if self._config.mode == "ask":
            self._bubble.show_for_image(self._dock)
        else:
            self._start_ocr()

    def _start_ocr(self) -> None:
        if self._pending_image is not None:
            self._ocr.recognize_clipboard_image(self._pending_image)
            self._pending_image = None

    def _toggle_playback_pause(self) -> None:
        self._player.toggle_pause()

    def _stop(self) -> None:
        self._speech.stop()
        self._player.stop()
        self._set_state("idle")

    def _replay_last(self) -> None:
        if self._last_text:
            self._speak(self._last_text)

    def _on_playback_finished(self) -> None:
        logger.info("playback_finished")
        self._set_state("idle")

    def _set_state(self, state: str, detail: str = "") -> None:
        self._dock.set_state(state)
        self._tray.set_state(state, detail)

    def _on_capture_error(self, code: str) -> None:
        key = f"clipboard.{code}"
        message = self._translator.text(key)
        logger.warning("selection_capture_failed code=%s", code)
        self._tray.show_message(
            self._translator.text("error.title"),
            message,
            QSystemTrayIcon.MessageIcon.Warning,
        )

    def _on_hotkey_registration(self, action: str, registered: bool, reason: str) -> None:
        if action == ACTION_READ and not registered:
            result = self._hotkeys.results.get(action)
            if reason == "hotkey conflict" and result is not None:
                message = self._translator.text("error.hotkey_conflict", hotkey=result.hotkey)
            else:
                message = self._translator.text("error.hotkey_unavailable")
            self._set_state("error", message)
            self._tray.show_message(
                self._translator.text("error.title"),
                message,
                QSystemTrayIcon.MessageIcon.Critical,
            )

    def _on_hotkey_error(self, reason: str) -> None:
        message = self._translator.text("error.hotkey_unavailable")
        logger.error("hotkey_unavailable reason=%s", reason)
        self._set_state("error", message)
        self._tray.show_message(
            self._translator.text("error.title"),
            message,
            QSystemTrayIcon.MessageIcon.Critical,
        )

    def _on_speech_error(self, reason: str) -> None:
        logger.error("tts_request_failed reason=%s", reason)
        message = localize_speech_error(self._translator, reason)
        self._set_state("error", message)
        self._tray.show_message(
            self._translator.text("error.title"), message, QSystemTrayIcon.MessageIcon.Critical
        )

    def _on_player_error(self, code: str) -> None:
        message = localize_audio_error(self._translator, code)
        self._set_state("error", message)
        self._tray.show_message(self._translator.text("error.title"), message)

    def _on_ocr_error(self, reason: str) -> None:
        logger.error("ocr_failed reason=%s", reason)
        message = localize_ocr_error(self._translator, reason)
        self._set_state("error", message)
        self._tray.show_message(self._translator.text("error.title"), message)

    def _set_mode(self, mode: str) -> None:
        self._config.set("trigger", "mode", mode)
        self._config.save()
        self._apply_clipboard_mode()

    def _set_clipboard_monitoring(self, enabled: bool) -> None:
        self._config.set("trigger", "clipboard_enabled", enabled)
        self._config.save()
        self._apply_clipboard_mode()

    def _apply_clipboard_mode(self) -> None:
        enabled = self._config.clipboard_enabled and self._config.mode != "manual"
        self._clipboard_watcher.set_enabled(enabled)

    def _set_hotkeys_enabled(self, enabled: bool) -> None:
        self._config.set("trigger", "hotkey_enabled", enabled)
        self._config.save()
        self._hotkeys.set_enabled(enabled)

    def _show_dock_menu(self, position: QPoint) -> None:
        self._tray.show_menu(position)

    def _show_settings(self) -> None:
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(
                self._config,
                self._translator,
                hotkeys=self._hotkeys,
                clipboard_watcher=self._clipboard_watcher,
                player=self._player,
                log_path=self._log_path,
            )
            self._settings_dialog.saved.connect(self._on_settings_saved)
            self._settings_dialog.finished.connect(self._clear_settings_reference)
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    def _clear_settings_reference(self, _result: int) -> None:
        self._settings_dialog = None

    def _on_settings_saved(self) -> None:
        self._config.reload()
        self._application.setStyleSheet(stylesheet_for_theme(self._config.theme, self._application))
        self._translator.set_language(self._config.language, persist=False)
        self._apply_clipboard_mode()
        self._hotkeys.start()
        self._tray.retranslate()
        self._tray.show_message(
            self._translator.text("app.name"),
            self._translator.text("notification.settings_saved"),
        )

    def _show_about(self) -> None:
        tr = self._translator.text
        QMessageBox.about(
            None,
            tr("action.about"),
            f"<b>{tr('app.name')}</b><br>{tr('about.version', version=__version__)}"
            f"<p>{tr('about.description')}</p><p>{tr('about.derived')}</p>",
        )

    def quit(self) -> None:
        self.shutdown()
        self._application.quit()

    def shutdown(self) -> None:
        if self._shutting_down:
            return
        self._shutting_down = True
        logger.info("shutdown_started")
        self._selection_capture.cancel()
        self._hotkeys.stop()
        self._speech.shutdown()
        self._ocr.stop()
        self._player.stop()
        self._config.save()
        _release_single_instance()


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    application = QApplication(sys.argv)
    application.setQuitOnLastWindowClosed(False)
    application.setApplicationName("Speak Helper")
    application.setApplicationVersion(__version__)
    config = Config()
    translator = Translator(config)
    if not _acquire_single_instance():
        QMessageBox.warning(
            None, translator.text("app.name"), translator.text("app.already_running")
        )
        raise SystemExit(0)
    controller = SpeakHelperApp(application)
    application.aboutToQuit.connect(controller.shutdown)
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(1_500, controller.quit)
    raise SystemExit(application.exec())


if __name__ == "__main__":
    main()
