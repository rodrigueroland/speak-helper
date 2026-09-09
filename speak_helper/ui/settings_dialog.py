"""Localized, responsive settings and diagnostics dialog."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import tempfile
import time
from pathlib import Path

import httpx
from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..audio_player import AudioPlayer
from ..clipboard_watcher import ClipboardWatcher
from ..config import Config
from ..diagnostics import collect_diagnostics, format_diagnostics
from ..error_messages import localize_speech_error
from ..hotkey_service import (
    ACTION_READ,
    READ_HOTKEY_CANDIDATES,
    HotkeyService,
    WindowsNativeHotkeyRegistrar,
    first_available_hotkey,
)
from ..i18n import Translator
from ..speech_service import build_openai_speech_payload
from ..startup_service import StartupService

logger = logging.getLogger(__name__)

EDGE_VOICES = (
    ("voice.en_us_aria", "en-US-AriaNeural"),
    ("voice.en_us_guy", "en-US-GuyNeural"),
    ("voice.en_gb_sonia", "en-GB-SoniaNeural"),
    ("voice.fr_fr_denise", "fr-FR-DeniseNeural"),
    ("voice.fr_fr_henri", "fr-FR-HenriNeural"),
    ("voice.fr_be_charline", "fr-BE-CharlineNeural"),
    ("voice.fr_ca_sylvie", "fr-CA-SylvieNeural"),
)


class _TtsTestWorker(QObject):
    result = Signal(bool, int, str)

    def __init__(
        self,
        backend: str,
        edge_voice: str,
        base_url: str,
        api_key: str,
        model: str,
        voice: str,
        provider_preset: str,
        language: str,
        timeout: int,
        test_phrase: str,
    ) -> None:
        super().__init__()
        self._backend = backend
        self._edge_voice = edge_voice
        self._base_url = base_url
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._provider_preset = provider_preset
        self._language = language
        self._timeout = timeout
        self._test_phrase = test_phrase

    def run(self) -> None:
        started = time.monotonic()
        temporary_path = ""
        try:
            if self._backend == "edge":
                import edge_tts

                handle, temporary_path = tempfile.mkstemp(suffix=".mp3")
                os.close(handle)
                asyncio.run(
                    edge_tts.Communicate(self._test_phrase, self._edge_voice).save(temporary_path)
                )
                if Path(temporary_path).stat().st_size == 0:
                    raise RuntimeError("The service returned empty audio")
            else:
                headers = {"Content-Type": "application/json"}
                if self._api_key:
                    headers["Authorization"] = f"Bearer {self._api_key}"
                response = httpx.post(
                    f"{self._base_url.rstrip('/')}/audio/speech",
                    headers=headers,
                    json=build_openai_speech_payload(
                        model=self._model,
                        text=self._test_phrase,
                        voice=self._voice,
                        speed=1.0,
                        audio_format="mp3",
                        provider_preset=self._provider_preset,
                        language=self._language,
                    ),
                    timeout=self._timeout,
                )
                response.raise_for_status()
                if not response.content:
                    raise RuntimeError("The service returned empty audio")
            duration = int((time.monotonic() - started) * 1_000)
            self.result.emit(True, duration, "")
        except Exception as exc:
            self.result.emit(False, 0, str(exc))
        finally:
            if temporary_path:
                with contextlib.suppress(OSError):
                    Path(temporary_path).unlink()


class SettingsDialog(QDialog):
    saved = Signal()

    def __init__(
        self,
        config: Config,
        translator: Translator,
        *,
        hotkeys: HotkeyService,
        clipboard_watcher: ClipboardWatcher,
        player: AudioPlayer,
        log_path: Path,
        startup_service: StartupService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._translator = translator
        self._hotkeys = hotkeys
        self._clipboard_watcher = clipboard_watcher
        self._player = player
        self._log_path = log_path
        self._startup_service = startup_service or StartupService()
        self._labels: list[tuple[QLabel, str]] = []
        self._texts: list[tuple[QWidget, str]] = []
        self._navigation_keys = [
            "tab.general",
            "tab.speech",
            "tab.hotkeys",
            "tab.clipboard",
            "tab.ocr",
            "tab.appearance",
            "tab.cache",
            "tab.diagnostics",
            "tab.about",
        ]
        self._test_thread: QThread | None = None
        self._test_worker: _TtsTestWorker | None = None
        self.setMinimumSize(780, 640)
        self.resize(860, 700)
        self._build_ui()
        self._load_values()
        self._hotkeys.test_triggered.connect(self._hotkey_test_completed)
        self.finished.connect(lambda: self._hotkeys.cancel_test())
        self._translator.language_changed.connect(self.retranslate)
        self.retranslate()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        body = QHBoxLayout()
        body.setSpacing(0)
        self._navigation = QListWidget()
        self._navigation.setMinimumWidth(175)
        self._navigation.setMaximumWidth(220)
        self._stack = QStackedWidget()
        pages = (
            self._general_page(),
            self._speech_page(),
            self._hotkeys_page(),
            self._clipboard_page(),
            self._ocr_page(),
            self._appearance_page(),
            self._cache_page(),
            self._diagnostics_page(),
            self._about_page(),
        )
        for page in pages:
            self._stack.addWidget(self._scrollable(page))
        self._navigation.currentRowChanged.connect(self._stack.setCurrentIndex)
        self._navigation.setCurrentRow(0)
        body.addWidget(self._navigation)
        body.addWidget(self._stack, 1)
        root.addLayout(body, 1)

        self._buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._save_button = self._buttons.button(QDialogButtonBox.StandardButton.Save)
        self._save_button.setProperty("primary", True)
        self._buttons.accepted.connect(self._save)
        self._buttons.rejected.connect(self.reject)
        root.addWidget(self._buttons)

    @staticmethod
    def _scrollable(page: QWidget) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(page)
        return scroll

    @staticmethod
    def _page() -> tuple[QWidget, QVBoxLayout]:
        page = QWidget()
        page.setMinimumWidth(0)
        page.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        return page, layout

    def _add_row(self, form: QFormLayout, key: str, widget: QWidget) -> None:
        label = QLabel()
        label.setBuddy(widget)
        self._labels.append((label, key))
        form.addRow(label, widget)

    def _bind_text(self, widget: QWidget, key: str) -> QWidget:
        self._texts.append((widget, key))
        return widget

    def _general_page(self) -> QWidget:
        page, layout = self._page()
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        self._language = QComboBox()
        self._language.addItem("English", "en")
        self._language.addItem("Français", "fr")
        self._language.currentIndexChanged.connect(self._language_selected)
        self._add_row(form, "settings.language", self._language)
        self._mode = QComboBox()
        self._add_row(form, "mode.title", self._mode)
        layout.addLayout(form)
        self._autostart = QCheckBox()
        self._bind_text(self._autostart, "settings.autostart")
        self._autostart.setEnabled(self._startup_service.supported)
        layout.addWidget(self._autostart)
        layout.addStretch()
        return page

    def _speech_page(self) -> QWidget:
        page, layout = self._page()
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        self._provider = QComboBox()
        self._provider.currentIndexChanged.connect(self._update_provider_controls)
        self._provider.activated.connect(self._provider_activated)
        self._add_row(form, "settings.provider", self._provider)
        self._edge_voice = QComboBox()
        for label_key, identifier in EDGE_VOICES:
            self._edge_voice.addItem(self._translator.text(label_key), identifier)
        self._add_row(form, "settings.edge_voice", self._edge_voice)
        self._base_url = QLineEdit()
        self._add_row(form, "settings.base_url", self._base_url)
        self._model = QLineEdit()
        self._add_row(form, "settings.model", self._model)
        self._voice = QLineEdit()
        self._add_row(form, "settings.voice", self._voice)
        api_row = QWidget()
        api_layout = QHBoxLayout(api_row)
        api_layout.setContentsMargins(0, 0, 0, 0)
        self._api_key = QLineEdit()
        self._api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._api_key.setPlaceholderText(self._translator.text("settings.api_key_optional"))
        self._show_key = QPushButton()
        self._show_key.clicked.connect(self._toggle_api_key)
        api_layout.addWidget(self._api_key)
        api_layout.addWidget(self._show_key)
        self._add_row(form, "settings.api_key", api_row)
        self._timeout = QSpinBox()
        self._timeout.setRange(1, 300)
        self._timeout.setSuffix(" s")
        self._add_row(form, "settings.timeout", self._timeout)
        self._speed = QDoubleSpinBox()
        self._speed.setRange(0.5, 2.0)
        self._speed.setSingleStep(0.1)
        self._speed.setSuffix("×")
        self._add_row(form, "settings.speed", self._speed)
        self._sentences = QSpinBox()
        self._sentences.setRange(1, 20)
        self._add_row(form, "settings.sentences_per_chunk", self._sentences)
        layout.addLayout(form)
        test_row = QHBoxLayout()
        self._test_tts_button = QPushButton()
        self._test_tts_button.clicked.connect(self._test_tts)
        self._test_result = QLabel()
        test_row.addWidget(self._test_tts_button)
        test_row.addWidget(self._test_result, 1)
        layout.addLayout(test_row)
        preprocessing_title = QLabel()
        preprocessing_title.setProperty("section", True)
        self._bind_text(preprocessing_title, "settings.preprocessing")
        layout.addWidget(preprocessing_title)
        self._preprocessing_enabled = QCheckBox()
        self._strip_markdown = QCheckBox()
        self._preserve_code = QCheckBox()
        self._bind_text(self._preprocessing_enabled, "settings.preprocessing_enabled")
        self._bind_text(self._strip_markdown, "settings.strip_markdown")
        self._bind_text(self._preserve_code, "settings.preserve_code")
        self._preprocessing_enabled.toggled.connect(self._update_preprocessing_controls)
        layout.addWidget(self._preprocessing_enabled)
        layout.addWidget(self._strip_markdown)
        layout.addWidget(self._preserve_code)
        preprocessing_form = QFormLayout()
        self._url_mode = QComboBox()
        self._add_row(preprocessing_form, "settings.url_mode", self._url_mode)
        layout.addLayout(preprocessing_form)
        layout.addStretch()
        return page

    def _hotkeys_page(self) -> QWidget:
        page, layout = self._page()
        self._enable_hotkeys = QCheckBox()
        self._bind_text(self._enable_hotkeys, "settings.enable_hotkeys")
        layout.addWidget(self._enable_hotkeys)
        form = QFormLayout()
        self._read_hotkey = QLineEdit()
        self._stop_hotkey = QLineEdit()
        self._pause_hotkey = QLineEdit()
        self._replay_hotkey = QLineEdit()
        self._add_row(form, "hotkey.read", self._read_hotkey)
        self._add_row(form, "hotkey.stop", self._stop_hotkey)
        self._add_row(form, "hotkey.pause", self._pause_hotkey)
        self._add_row(form, "hotkey.replay", self._replay_hotkey)
        layout.addLayout(form)
        suggestion_row = QHBoxLayout()
        self._suggest_hotkey = QPushButton()
        self._suggest_hotkey.clicked.connect(self._suggest_read_hotkey)
        self._suggest_hotkey_result = QLabel()
        self._suggest_hotkey_result.setWordWrap(True)
        suggestion_row.addWidget(self._suggest_hotkey)
        suggestion_row.addWidget(self._suggest_hotkey_result, 1)
        layout.addLayout(suggestion_row)
        layout.addStretch()
        return page

    def _clipboard_page(self) -> QWidget:
        page, layout = self._page()
        self._clipboard_monitor = QCheckBox()
        self._restore_clipboard = QCheckBox()
        self._bind_text(self._clipboard_monitor, "settings.clipboard_monitor")
        self._bind_text(self._restore_clipboard, "clipboard.restore")
        layout.addWidget(self._clipboard_monitor)
        layout.addWidget(self._restore_clipboard)
        form = QFormLayout()
        self._capture_timeout = QSpinBox()
        self._capture_timeout.setRange(250, 10_000)
        self._capture_timeout.setSuffix(" ms")
        self._max_length = QSpinBox()
        self._max_length.setRange(10, 200_000)
        self._add_row(form, "settings.capture_timeout", self._capture_timeout)
        self._add_row(form, "settings.max_length", self._max_length)
        layout.addLayout(form)
        layout.addStretch()
        return page

    def _ocr_page(self) -> QWidget:
        page, layout = self._page()
        self._ocr_enabled = QCheckBox()
        self._bind_text(self._ocr_enabled, "settings.enable_ocr")
        layout.addWidget(self._ocr_enabled)
        description = QLabel()
        description.setWordWrap(True)
        description.setProperty("muted", True)
        self._bind_text(description, "ocr.description")
        layout.addWidget(description)
        form = QFormLayout()
        self._ocr_model = QLineEdit()
        self._add_row(form, "settings.ocr_model", self._ocr_model)
        layout.addLayout(form)
        layout.addStretch()
        return page

    def _appearance_page(self) -> QWidget:
        page, layout = self._page()
        form = QFormLayout()
        self._theme = QComboBox()
        for theme in ("system", "light", "dark"):
            self._theme.addItem("", theme)
        self._add_row(form, "settings.theme", self._theme)
        layout.addLayout(form)
        layout.addStretch()
        return page

    def _cache_page(self) -> QWidget:
        page, layout = self._page()
        self._cache_enabled = QCheckBox()
        self._bind_text(self._cache_enabled, "settings.cache_enabled")
        layout.addWidget(self._cache_enabled)
        form = QFormLayout()
        self._cache_limit = QSpinBox()
        self._cache_limit.setRange(0, 10_000)
        self._cache_limit.setSuffix(" MB")
        self._add_row(form, "settings.cache_limit", self._cache_limit)
        layout.addLayout(form)
        self._cache_usage = QLabel()
        layout.addWidget(self._cache_usage)
        self._clear_cache = QPushButton()
        self._clear_cache.clicked.connect(self._clear_cache_files)
        layout.addWidget(self._clear_cache)
        layout.addStretch()
        return page

    def _diagnostics_page(self) -> QWidget:
        page, layout = self._page()
        self._diagnostics_form = QFormLayout()
        self._diagnostics_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        self._diagnostic_values: dict[str, QLabel] = {}
        keys = (
            "app_version",
            "operating_system",
            "python_version",
            "language",
            "read_hotkey",
            "hotkey_registered",
            "clipboard_watcher_active",
            "tts_backend",
            "tts_endpoint",
            "tts_model",
            "audio_state",
            "audio_output_available",
            "audio_output_device",
            "cache_path",
            "log_path",
        )
        label_keys = (
            "diagnostics.app_version",
            "diagnostics.os",
            "diagnostics.python",
            "diagnostics.language",
            "diagnostics.hotkey",
            "diagnostics.hotkey_status",
            "diagnostics.clipboard",
            "diagnostics.tts_backend",
            "diagnostics.endpoint",
            "diagnostics.model",
            "diagnostics.audio_state",
            "diagnostics.audio_available",
            "diagnostics.audio_device",
            "diagnostics.cache_path",
            "diagnostics.log_path",
        )
        for name, label_key in zip(keys, label_keys, strict=True):
            value = QLabel()
            value.setWordWrap(True)
            value.setMinimumWidth(0)
            value.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            value.setTextInteractionFlags(
                value.textInteractionFlags() | Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._diagnostic_values[name] = value
            self._add_row(self._diagnostics_form, label_key, value)
        layout.addLayout(self._diagnostics_form)
        primary_actions = QHBoxLayout()
        self._test_hotkey = QPushButton()
        self._test_hotkey.clicked.connect(self._diagnose_hotkey)
        self._test_clipboard = QPushButton()
        self._test_clipboard.clicked.connect(self._diagnose_clipboard)
        primary_actions.addWidget(self._test_hotkey)
        primary_actions.addWidget(self._test_clipboard)
        layout.addLayout(primary_actions)
        secondary_actions = QHBoxLayout()
        self._copy_diagnostics = QPushButton()
        self._copy_diagnostics.clicked.connect(self._copy_diagnostics_text)
        self._open_logs = QPushButton()
        self._open_logs.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._log_path.parent)))
        )
        secondary_actions.addWidget(self._copy_diagnostics)
        secondary_actions.addWidget(self._open_logs)
        layout.addLayout(secondary_actions)
        self._diagnostic_result = QLabel()
        layout.addWidget(self._diagnostic_result)
        layout.addStretch()
        return page

    def _about_page(self) -> QWidget:
        page, layout = self._page()
        title = QLabel("<h2>Speak Helper</h2>")
        layout.addWidget(title)
        self._about_version = QLabel()
        self._about_description = QLabel()
        self._about_description.setWordWrap(True)
        self._about_derived = QLabel()
        self._about_derived.setWordWrap(True)
        layout.addWidget(self._about_version)
        layout.addWidget(self._about_description)
        layout.addWidget(self._about_derived)
        layout.addStretch()
        return page

    def _load_values(self) -> None:
        config = self._config
        self._language.setCurrentIndex(max(0, self._language.findData(config.language)))
        self._reload_mode_items(config.mode)
        self._autostart.setChecked(self._startup_service.is_enabled())
        provider = str(config.get("tts", "provider_preset", default="custom"))
        provider_data = "edge" if config.backend == "edge" else provider
        self._reload_provider_items(provider_data)
        edge_index = self._edge_voice.findData(config.edge_voice)
        self._edge_voice.setCurrentIndex(edge_index if edge_index >= 0 else 0)
        self._base_url.setText(config.base_url)
        self._model.setText(config.model)
        self._voice.setText(config.voice)
        self._api_key.setText(config.api_key)
        self._timeout.setValue(config.timeout_sec)
        self._speed.setValue(config.speed)
        self._sentences.setValue(config.sentences_per_chunk)
        self._preprocessing_enabled.setChecked(
            bool(config.get("preprocessing", "enabled", default=True))
        )
        self._strip_markdown.setChecked(
            bool(config.get("preprocessing", "strip_markdown_markers", default=True))
        )
        self._preserve_code.setChecked(
            bool(config.get("preprocessing", "preserve_code", default=True))
        )
        self._reload_url_mode_items(str(config.get("preprocessing", "url_mode", default="keep")))
        self._update_preprocessing_controls()
        self._enable_hotkeys.setChecked(config.hotkey_enabled)
        self._read_hotkey.setText(config.hotkey)
        self._stop_hotkey.setText(config.stop_hotkey)
        self._pause_hotkey.setText(config.pause_hotkey)
        self._replay_hotkey.setText(config.replay_hotkey)
        self._clipboard_monitor.setChecked(config.clipboard_enabled)
        self._restore_clipboard.setChecked(config.restore_clipboard)
        self._capture_timeout.setValue(config.capture_timeout_ms)
        self._max_length.setValue(config.max_length)
        self._ocr_enabled.setChecked(config.ocr_enabled)
        self._ocr_model.setText(config.ocr_model)
        theme = str(config.get("ui", "theme", default="system"))
        self._theme.setCurrentIndex(max(0, self._theme.findData(theme)))
        self._cache_enabled.setChecked(config.cache_enabled)
        self._cache_limit.setValue(config.cache_max_mb)
        self._refresh_cache_usage()
        self._refresh_diagnostics()

    def retranslate(self) -> None:
        tr = self._translator.text
        self.setWindowTitle(tr("settings.title"))
        current_row = self._navigation.currentRow()
        self._navigation.clear()
        self._navigation.addItems([tr(key) for key in self._navigation_keys])
        self._navigation.setCurrentRow(max(0, current_row))
        for label, key in self._labels:
            label.setText(tr(key))
        for widget, key in self._texts:
            widget.setProperty("text", tr(key))
        self._save_button.setText(tr("action.save"))
        self._buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("action.cancel"))
        self._show_key.setText(tr("settings.show_key"))
        self._test_tts_button.setText(tr("action.test_tts"))
        self._clear_cache.setText(tr("settings.clear_cache"))
        self._test_hotkey.setText(tr("action.test_hotkey"))
        self._suggest_hotkey.setText(tr("action.suggest_hotkey"))
        self._test_clipboard.setText(tr("action.test_clipboard"))
        self._copy_diagnostics.setText(tr("action.copy_diagnostics"))
        self._open_logs.setText(tr("action.open_log_folder"))
        self._about_version.setText(tr("about.version", version=__version__))
        self._about_description.setText(tr("about.description"))
        self._about_derived.setText(tr("about.derived"))
        self._reload_edge_voices(self._edge_voice.currentData() or self._config.edge_voice)
        self._reload_mode_items(self._mode.currentData() or self._config.mode)
        self._reload_provider_items(self._provider.currentData() or "edge")
        self._reload_url_mode_items(self._url_mode.currentData() or "keep")
        selected_theme = self._theme.currentData() or "system"
        for index, theme in enumerate(("system", "light", "dark")):
            self._theme.setItemText(index, tr(f"theme.{theme}"))
        self._theme.setCurrentIndex(max(0, self._theme.findData(selected_theme)))
        self._refresh_cache_usage()
        self._refresh_diagnostics()

    def _reload_edge_voices(self, selected: str) -> None:
        self._edge_voice.blockSignals(True)
        self._edge_voice.clear()
        for label_key, identifier in EDGE_VOICES:
            self._edge_voice.addItem(self._translator.text(label_key), identifier)
        self._edge_voice.setCurrentIndex(max(0, self._edge_voice.findData(selected)))
        self._edge_voice.blockSignals(False)

    def _reload_mode_items(self, selected: str) -> None:
        self._mode.blockSignals(True)
        self._mode.clear()
        for mode in ("manual", "ask", "auto"):
            self._mode.addItem(self._translator.text(f"mode.{mode}"), mode)
        self._mode.setCurrentIndex(max(0, self._mode.findData(selected)))
        self._mode.blockSignals(False)

    def _reload_provider_items(self, selected: str) -> None:
        self._provider.blockSignals(True)
        self._provider.clear()
        for key, value in (
            ("backend.edge", "edge"),
            ("backend.openai", "custom"),
            ("backend.qwen_local", "qwen3_local"),
        ):
            self._provider.addItem(self._translator.text(key), value)
        self._provider.setCurrentIndex(max(0, self._provider.findData(selected)))
        self._provider.blockSignals(False)
        self._update_provider_controls()

    def _reload_url_mode_items(self, selected: str) -> None:
        self._url_mode.blockSignals(True)
        self._url_mode.clear()
        for mode in ("keep", "domain", "omit"):
            self._url_mode.addItem(self._translator.text(f"url.{mode}"), mode)
        self._url_mode.setCurrentIndex(max(0, self._url_mode.findData(selected)))
        self._url_mode.blockSignals(False)

    def _language_selected(self) -> None:
        language = self._language.currentData()
        if language:
            self._translator.set_language(str(language))

    def _update_provider_controls(self) -> None:
        provider = self._provider.currentData()
        is_edge = provider == "edge"
        self._edge_voice.setEnabled(is_edge)
        for widget in (self._base_url, self._model, self._voice, self._api_key):
            widget.setEnabled(not is_edge)

    def _update_preprocessing_controls(self) -> None:
        enabled = self._preprocessing_enabled.isChecked()
        self._strip_markdown.setEnabled(enabled)
        self._preserve_code.setEnabled(enabled)
        self._url_mode.setEnabled(enabled)

    def _provider_activated(self) -> None:
        self._update_provider_controls()
        if self._provider.currentData() == "qwen3_local":
            self._base_url.setText("http://127.0.0.1:8000/v1")
            self._model.setText("Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
            self._voice.setText("Vivian")

    def _toggle_api_key(self) -> None:
        hidden = self._api_key.echoMode() == QLineEdit.EchoMode.Password
        self._api_key.setEchoMode(
            QLineEdit.EchoMode.Normal if hidden else QLineEdit.EchoMode.Password
        )

    def _save(self) -> None:
        config = self._config
        autostart = self._autostart.isChecked()
        startup_result = self._startup_service.set_enabled(autostart)
        if not startup_result.success:
            logger.error("autostart_update_failed reason=%s", startup_result.reason)
            QMessageBox.critical(
                self,
                self._translator.text("error.title"),
                self._translator.text("error.startup"),
            )
            return
        config.set("ui", "autostart", autostart)
        provider = str(self._provider.currentData())
        config.set("tts", "backend", "edge" if provider == "edge" else "openai")
        config.set("tts", "provider_preset", provider)
        config.set("tts", "edge_voice", self._edge_voice.currentData())
        config.set("tts", "base_url", self._base_url.text().strip())
        config.set("tts", "model", self._model.text().strip())
        config.set("tts", "voice", self._voice.text().strip())
        config.api_key = self._api_key.text()
        config.set("tts", "timeout_sec", self._timeout.value())
        config.set("tts", "speed", self._speed.value())
        config.set("tts", "sentences_per_chunk", self._sentences.value())
        config.set("preprocessing", "enabled", self._preprocessing_enabled.isChecked())
        config.set("preprocessing", "strip_markdown_markers", self._strip_markdown.isChecked())
        config.set("preprocessing", "preserve_code", self._preserve_code.isChecked())
        config.set("preprocessing", "url_mode", self._url_mode.currentData())
        config.set("trigger", "mode", self._mode.currentData())
        config.set("trigger", "hotkey_enabled", self._enable_hotkeys.isChecked())
        config.set("trigger", "hotkey", self._read_hotkey.text().strip())
        config.set("trigger", "stop_hotkey", self._stop_hotkey.text().strip())
        config.set("trigger", "pause_hotkey", self._pause_hotkey.text().strip())
        config.set("trigger", "replay_hotkey", self._replay_hotkey.text().strip())
        config.set("trigger", "clipboard_enabled", self._clipboard_monitor.isChecked())
        config.set("trigger", "max_length", self._max_length.value())
        config.set("clipboard", "restore_after_capture", self._restore_clipboard.isChecked())
        config.set("clipboard", "capture_timeout_ms", self._capture_timeout.value())
        config.set("ocr", "enabled", self._ocr_enabled.isChecked())
        config.set("ocr", "model", self._ocr_model.text().strip())
        config.set("ui", "theme", self._theme.currentData())
        config.set("cache", "enabled", self._cache_enabled.isChecked())
        config.set("cache", "max_mb", self._cache_limit.value())
        config.save()
        self.saved.emit()
        self.accept()

    def _test_tts(self) -> None:
        if self._test_thread and self._test_thread.isRunning():
            return
        self._test_tts_button.setEnabled(False)
        self._test_result.setText(self._translator.text("test.running"))
        backend = "edge" if self._provider.currentData() == "edge" else "openai"
        self._test_thread = QThread(self)
        self._test_worker = _TtsTestWorker(
            backend,
            str(self._edge_voice.currentData()),
            self._base_url.text().strip(),
            self._api_key.text().strip(),
            self._model.text().strip(),
            self._voice.text().strip(),
            str(self._provider.currentData()),
            self._translator.language,
            self._timeout.value(),
            self._translator.text("test.tts_phrase"),
        )
        self._test_worker.moveToThread(self._test_thread)
        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.result.connect(self._test_finished)
        self._test_worker.result.connect(self._test_thread.quit)
        self._test_thread.finished.connect(self._test_worker.deleteLater)
        self._test_thread.finished.connect(self._test_thread.deleteLater)
        self._test_thread.finished.connect(self._clear_test_worker)
        self._test_thread.start()

    def _clear_test_worker(self) -> None:
        self._test_worker = None
        self._test_thread = None

    def _test_finished(self, success: bool, duration_ms: int, reason: str) -> None:
        self._test_tts_button.setEnabled(True)
        key = "test.success" if success else "test.failed"
        user_reason = reason if success else localize_speech_error(self._translator, reason)
        self._test_result.setText(
            self._translator.text(key, duration_ms=duration_ms, reason=user_reason)
        )
        self._test_result.setProperty("result", "success" if success else "error")
        self._test_result.style().unpolish(self._test_result)
        self._test_result.style().polish(self._test_result)

    def _refresh_cache_usage(self) -> None:
        total = sum(
            path.stat().st_size for path in self._config.cache_dir.glob("*") if path.is_file()
        )
        self._cache_usage.setText(
            self._translator.text(
                "settings.cache_usage", used=total / 1024 / 1024, limit=self._cache_limit.value()
            )
        )

    def _clear_cache_files(self) -> None:
        for path in self._config.cache_dir.glob("*"):
            if path.is_file():
                with contextlib.suppress(OSError):
                    path.unlink()
        self._refresh_cache_usage()

    def _snapshot(self):
        return collect_diagnostics(
            self._config,
            self._hotkeys,
            self._clipboard_watcher,
            self._player,
            self._log_path,
        )

    def _refresh_diagnostics(self) -> None:
        snapshot = self._snapshot()
        for name, label in self._diagnostic_values.items():
            value = getattr(snapshot, name)
            if isinstance(value, bool):
                if name == "hotkey_registered":
                    value = self._translator.text(
                        "status.registered" if value else "status.unregistered"
                    )
                else:
                    value = self._translator.text("status.enabled" if value else "status.disabled")
            elif name == "audio_state":
                value = self._translator.text(f"status.{value}")
            elif name == "audio_output_device" and not value:
                value = self._translator.text("status.unavailable")
            label.setText(str(value))

    def _copy_diagnostics_text(self) -> None:
        QGuiApplication.clipboard().setText(format_diagnostics(self._snapshot()))

    def _diagnose_clipboard(self) -> None:
        mime = QGuiApplication.clipboard().mimeData()
        key = "test.success" if mime is not None and mime.hasText() else "clipboard.empty"
        self._diagnostic_result.setText(
            self._translator.text(key, duration_ms=0)
            if key == "test.success"
            else self._translator.text(key)
        )

    def _diagnose_hotkey(self) -> None:
        if self._hotkeys.arm_test(ACTION_READ):
            self._diagnostic_result.setText(
                self._translator.text("test.hotkey_press", hotkey=self._config.hotkey)
            )
        else:
            self._diagnostic_result.setText(self._translator.text("test.hotkey_unavailable"))

    def _suggest_read_hotkey(self) -> None:
        reserved = (
            self._stop_hotkey.text(),
            self._pause_hotkey.text(),
            self._replay_hotkey.text(),
        )
        suggestion = first_available_hotkey(
            READ_HOTKEY_CANDIDATES,
            reserved=reserved,
            probe=WindowsNativeHotkeyRegistrar.is_available,
        )
        if suggestion is None:
            self._suggest_hotkey_result.setText(self._translator.text("hotkey.suggestion_none"))
            return
        self._read_hotkey.setText(suggestion)
        self._suggest_hotkey_result.setText(
            self._translator.text("hotkey.suggestion", hotkey=suggestion)
        )

    def _hotkey_test_completed(self, action: str) -> None:
        if action == ACTION_READ:
            self._diagnostic_result.setText(self._translator.text("test.hotkey_success"))
