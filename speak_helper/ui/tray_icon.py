"""Localized system-tray icon and command menu."""

from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from ..assets import ICON_ERROR, ICON_IDLE, ICON_PAUSED, ICON_SPEAKING
from ..config import Config
from ..i18n import Translator
from .theme import application_stylesheet


def _make_icon(svg: str, size: int = 22) -> QIcon:
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    QSvgRenderer(bytearray(svg.encode())).render(painter)
    painter.end()
    return QIcon(pixmap)


class TrayIcon(QObject):
    read_requested = Signal()
    pause_requested = Signal()
    stop_requested = Signal()
    replay_requested = Signal()
    mode_changed = Signal(str)
    clipboard_toggled = Signal(bool)
    hotkey_toggled = Signal(bool)
    settings_requested = Signal()
    about_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self, config: Config, translator: Translator, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._translator = translator
        self._paused = False
        self._state = "idle"
        self._icons = {
            "idle": _make_icon(ICON_IDLE),
            "speaking": _make_icon(ICON_SPEAKING),
            "paused": _make_icon(ICON_PAUSED),
            "error": _make_icon(ICON_ERROR),
        }
        self._tray = QSystemTrayIcon(self._icons["idle"], self)
        self._menu = QMenu()
        self._menu.setStyleSheet(application_stylesheet())
        self._build_menu()
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)
        self._translator.language_changed.connect(self.retranslate)
        self.retranslate()
        self._tray.show()

    def _build_menu(self) -> None:
        self._status_action = self._menu.addAction("")
        self._status_action.setEnabled(False)
        self._menu.addSeparator()

        self._read_action = self._menu.addAction("")
        self._read_action.triggered.connect(self.read_requested)
        self._pause_action = self._menu.addAction("")
        self._pause_action.triggered.connect(self.pause_requested)
        self._stop_action = self._menu.addAction("")
        self._stop_action.triggered.connect(self.stop_requested)
        self._replay_action = self._menu.addAction("")
        self._replay_action.triggered.connect(self.replay_requested)
        self._menu.addSeparator()

        self._mode_title = self._menu.addAction("")
        self._mode_title.setEnabled(False)
        mode_group = QActionGroup(self._menu)
        mode_group.setExclusive(True)
        self._manual_action = self._mode_action("manual", mode_group)
        self._ask_action = self._mode_action("ask", mode_group)
        self._auto_action = self._mode_action("auto", mode_group)
        self._menu.addSeparator()

        self._clipboard_action = self._menu.addAction("")
        self._clipboard_action.setCheckable(True)
        self._clipboard_action.setChecked(self._config.clipboard_enabled)
        self._clipboard_action.triggered.connect(self.clipboard_toggled)
        self._hotkey_action = self._menu.addAction("")
        self._hotkey_action.setCheckable(True)
        self._hotkey_action.setChecked(self._config.hotkey_enabled)
        self._hotkey_action.triggered.connect(self.hotkey_toggled)
        self._menu.addSeparator()

        self._settings_action = self._menu.addAction("")
        self._settings_action.triggered.connect(self.settings_requested)
        self._about_action = self._menu.addAction("")
        self._about_action.triggered.connect(self.about_requested)
        self._quit_action = self._menu.addAction("")
        self._quit_action.triggered.connect(self.quit_requested)

    def _mode_action(self, mode: str, group: QActionGroup) -> QAction:
        action = self._menu.addAction("")
        action.setCheckable(True)
        action.setChecked(self._config.mode == mode)
        action.triggered.connect(
            lambda _checked=False, selected=mode: self.mode_changed.emit(selected)
        )
        group.addAction(action)
        return action

    def set_state(self, state: str, detail: str = "") -> None:
        self._state = state
        self._paused = state == "paused"
        self._tray.setIcon(self._icons.get(state, self._icons["idle"]))
        status = self._translator.text(f"status.{state}")
        if detail and state == "error":
            status = f"{status}: {detail}"
        tooltip = self._translator.text("tray.tooltip", status=status)
        self._tray.setToolTip(tooltip)
        self._status_action.setText(tooltip)
        self._pause_action.setText(
            self._translator.text("action.resume" if self._paused else "action.pause")
        )

    def show_message(
        self,
        title: str,
        message: str,
        icon: QSystemTrayIcon.MessageIcon = QSystemTrayIcon.MessageIcon.Information,
    ) -> None:
        self._tray.showMessage(title, message, icon, 4_000)

    def show_menu(self, position: QPoint) -> None:
        self._menu.exec(position)

    def retranslate(self) -> None:
        tr = self._translator.text
        self._read_action.setText(f"{tr('action.read_selection')}\t{self._config.hotkey}")
        self._pause_action.setText(tr("action.resume" if self._paused else "action.pause"))
        self._stop_action.setText(f"{tr('action.stop')}\t{self._config.stop_hotkey}")
        self._replay_action.setText(f"{tr('action.replay')}\t{self._config.replay_hotkey}")
        self._mode_title.setText(tr("mode.title"))
        self._manual_action.setText(tr("mode.manual"))
        self._ask_action.setText(tr("mode.ask"))
        self._auto_action.setText(tr("mode.auto"))
        self._clipboard_action.setText(tr("settings.clipboard_monitor"))
        self._hotkey_action.setText(tr("settings.enable_hotkeys"))
        self._settings_action.setText(tr("settings.title"))
        self._about_action.setText(tr("action.about"))
        self._quit_action.setText(tr("action.quit"))
        self.set_state(self._state)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.settings_requested.emit()
