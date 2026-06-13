"""系统托盘图标及右键菜单"""
from __future__ import annotations

from PySide6.QtCore import QObject, QPoint, Signal
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from ..assets import ICON_ERROR, ICON_IDLE, ICON_PAUSED, ICON_SPEAKING
from ..config import Config


def _make_icon(svg_str: str, size: int = 22) -> QIcon:
    """将 SVG 字符串渲染成指定大小的 QIcon"""
    pix = QPixmap(size, size)
    pix.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pix)
    renderer = QSvgRenderer(bytearray(svg_str.encode()))
    renderer.render(painter)
    painter.end()
    return QIcon(pix)


class TrayIcon(QObject):
    pause_toggled = Signal(bool)        # True = 暂停
    stop_requested = Signal()
    replay_requested = Signal()
    mode_changed = Signal(str)          # "ask" | "auto"
    clipboard_toggled = Signal(bool)
    hotkey_toggled = Signal(bool)
    settings_requested = Signal()
    about_requested = Signal()
    quit_requested = Signal()

    def __init__(self, config: Config, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._paused = False
        self._icons = {
            "idle":     _make_icon(ICON_IDLE),
            "speaking": _make_icon(ICON_SPEAKING),
            "paused":   _make_icon(ICON_PAUSED),
            "error":    _make_icon(ICON_ERROR),
        }
        self._tray = QSystemTrayIcon(self._icons["idle"], self)
        self._build_menu()
        self._tray.setToolTip("Speak Helper · 监听中")
        self._tray.activated.connect(self._on_activated)
        self._tray.show()

    # ── public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str, detail: str = "") -> None:
        icon = self._icons.get(state, self._icons["idle"])
        self._tray.setIcon(icon)
        labels = {
            "idle":     "Speak Helper · 监听中",
            "speaking": f"Speak Helper · 朗读中 {detail}".strip(),
            "paused":   "Speak Helper · 已暂停",
            "error":    f"Speak Helper · 错误：{detail}",
        }
        self._tray.setToolTip(labels.get(state, "Speak Helper"))
        # 更新菜单头部
        self._status_action.setText(f"🔊  Speak Helper · {labels.get(state,'').split('·')[-1].strip()}")

    def show_message(self, title: str, msg: str) -> None:
        self._tray.showMessage(title, msg, QSystemTrayIcon.MessageIcon.Information, 3000)

    # ── menu builder ─────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menu = QMenu()
        menu.setStyleSheet(
            "QMenu{background:#FFFFFF;border:1px solid #E5E7EB;"
            "border-radius:8px;padding:4px 0;font-size:13px;}"
            "QMenu::item{padding:6px 20px;color:#111827;}"
            "QMenu::item:selected{background:#EFF6FF;color:#1D4ED8;}"
            "QMenu::separator{height:1px;background:#F3F4F6;margin:4px 0;}"
            "QMenu::item:disabled{color:#9CA3AF;}"
        )

        # 状态头（不可点击）
        self._status_action = QAction("🔊  Speak Helper · 监听中", menu)
        self._status_action.setEnabled(False)
        menu.addAction(self._status_action)
        menu.addSeparator()

        # 暂停/继续
        self._pause_action = QAction("⏸   暂停监听", menu)
        self._pause_action.triggered.connect(self._on_pause_toggle)
        menu.addAction(self._pause_action)

        # 重读
        replay = QAction("🔁  重读上一条\t Ctrl+Alt+R", menu)
        replay.triggered.connect(self.replay_requested)
        menu.addAction(replay)

        # 停止朗读
        stop = QAction("⏹   停止当前朗读", menu)
        stop.triggered.connect(self.stop_requested)
        menu.addAction(stop)

        menu.addSeparator()

        # 模式
        mode_label = QAction("模式", menu)
        mode_label.setEnabled(False)
        menu.addAction(mode_label)

        mode_group = QActionGroup(menu)
        mode_group.setExclusive(True)

        self._ask_action = QAction("   ◉ 询问（每次弹气泡）", menu)
        self._ask_action.setCheckable(True)
        self._ask_action.setChecked(self._config.mode == "ask")
        self._ask_action.triggered.connect(lambda: self.mode_changed.emit("ask"))
        mode_group.addAction(self._ask_action)
        menu.addAction(self._ask_action)

        self._auto_action = QAction("   ○ 自动（直接朗读）", menu)
        self._auto_action.setCheckable(True)
        self._auto_action.setChecked(self._config.mode == "auto")
        self._auto_action.triggered.connect(lambda: self.mode_changed.emit("auto"))
        mode_group.addAction(self._auto_action)
        menu.addAction(self._auto_action)

        menu.addSeparator()

        # 开关
        self._clip_action = QAction("📋  剪贴板触发", menu)
        self._clip_action.setCheckable(True)
        self._clip_action.setChecked(self._config.clipboard_enabled)
        self._clip_action.triggered.connect(
            lambda checked: self.clipboard_toggled.emit(checked)
        )
        menu.addAction(self._clip_action)

        self._hotkey_action = QAction("⌨   快捷键", menu)
        self._hotkey_action.setCheckable(True)
        self._hotkey_action.setChecked(self._config.hotkey_enabled)
        self._hotkey_action.triggered.connect(
            lambda checked: self.hotkey_toggled.emit(checked)
        )
        menu.addAction(self._hotkey_action)

        menu.addSeparator()

        settings = QAction("⚙   设置…", menu)
        settings.triggered.connect(self.settings_requested)
        menu.addAction(settings)

        about = QAction("ℹ   关于", menu)
        about.triggered.connect(self.about_requested)
        menu.addAction(about)

        quit_action = QAction("✕   退出", menu)
        quit_action.triggered.connect(self.quit_requested)
        menu.addAction(quit_action)

        self._menu = menu
        self._tray.setContextMenu(menu)

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_pause_toggle(self) -> None:
        self._paused = not self._paused
        self._pause_action.setText("▶   继续监听" if self._paused else "⏸   暂停监听")
        self.pause_toggled.emit(self._paused)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.settings_requested.emit()
