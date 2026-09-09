"""Settings UI smoke tests for both supported languages."""

from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication, QScrollArea

from speak_helper.audio_player import AudioPlayer
from speak_helper.clipboard_watcher import ClipboardWatcher
from speak_helper.config import Config
from speak_helper.hotkey_service import HotkeyService
from speak_helper.i18n import Translator
from speak_helper.ui.settings_dialog import SettingsDialog
from speak_helper.ui.theme import stylesheet_for_theme


def test_settings_dialog_retranslates_without_restart(qtbot, tmp_path):
    config = Config(config_dir=tmp_path, locale_name="en_US")
    translator = Translator(config)
    registrar = MagicMock()
    registrar.register.return_value = []
    dialog = SettingsDialog(
        config,
        translator,
        hotkeys=HotkeyService(config, registrar=registrar),
        clipboard_watcher=ClipboardWatcher(config),
        player=AudioPlayer(),
        log_path=tmp_path / "logs" / "speak-helper.log",
    )
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Settings"
    assert dialog._edge_voice.itemText(0) == "English (United States) · Aria"
    translator.set_language("fr")
    assert dialog.windowTitle() == "Paramètres"
    assert dialog._navigation.item(0).text() == "Général"
    assert dialog._edge_voice.itemText(0) == "Anglais (États-Unis) · Aria"


def test_qwen_preset_remains_editable(qtbot, tmp_path):
    config = Config(config_dir=tmp_path, locale_name="en_US")
    translator = Translator(config)
    registrar = MagicMock()
    registrar.register.return_value = []
    dialog = SettingsDialog(
        config,
        translator,
        hotkeys=HotkeyService(config, registrar=registrar),
        clipboard_watcher=ClipboardWatcher(config),
        player=AudioPlayer(),
        log_path=tmp_path / "app.log",
    )
    qtbot.addWidget(dialog)
    dialog._provider.setCurrentIndex(dialog._provider.findData("qwen3_local"))
    dialog._provider_activated()

    assert dialog._base_url.text() == "http://127.0.0.1:8000/v1"
    assert dialog._model.text() == "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    assert dialog._voice.text() == "Vivian"
    assert dialog._base_url.isEnabled()


def test_settings_reflect_actual_launch_at_login_state(qtbot, tmp_path):
    config = Config(config_dir=tmp_path, locale_name="en_US")
    translator = Translator(config)
    registrar = MagicMock()
    registrar.register.return_value = []
    startup = MagicMock()
    startup.supported = True
    startup.is_enabled.return_value = True
    dialog = SettingsDialog(
        config,
        translator,
        hotkeys=HotkeyService(config, registrar=registrar),
        clipboard_watcher=ClipboardWatcher(config),
        player=AudioPlayer(),
        log_path=tmp_path / "app.log",
        startup_service=startup,
    )
    qtbot.addWidget(dialog)

    assert dialog._autostart.isEnabled()
    assert dialog._autostart.isChecked()


@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("theme", ["light", "dark"])
def test_all_settings_pages_fit_minimum_size(qtbot, tmp_path, language, theme):
    config = Config(config_dir=tmp_path / f"{language}-{theme}", locale_name="en_US")
    config.set("ui", "language", language)
    config.set("ui", "theme", theme)
    translator = Translator(config)
    registrar = MagicMock()
    registrar.register.return_value = []
    startup = MagicMock()
    startup.supported = True
    startup.is_enabled.return_value = False
    application = QApplication.instance()
    assert application is not None
    application.setStyleSheet(stylesheet_for_theme(theme, application))
    dialog = SettingsDialog(
        config,
        translator,
        hotkeys=HotkeyService(config, registrar=registrar),
        clipboard_watcher=ClipboardWatcher(config),
        player=AudioPlayer(),
        log_path=tmp_path / "app.log",
        startup_service=startup,
    )
    qtbot.addWidget(dialog)
    dialog.resize(dialog.minimumSize())
    dialog.show()
    qtbot.waitExposed(dialog)

    for page_index in range(dialog._stack.count()):
        dialog._navigation.setCurrentRow(page_index)
        application.processEvents()
        scroll = dialog._stack.currentWidget()
        assert isinstance(scroll, QScrollArea)
        assert scroll.horizontalScrollBar().maximum() == 0, (
            f"page={page_index} content={scroll.widget().size().width()} "
            f"viewport={scroll.viewport().width()}"
        )

    assert dialog._save_button.isVisible()
    assert dialog._buttons.button(dialog._buttons.StandardButton.Cancel).isVisible()
