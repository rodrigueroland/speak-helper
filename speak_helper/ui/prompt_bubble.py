"""Keyboard-accessible confirmation bubble for ask-before-reading mode."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeyEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..config import Config
from ..i18n import Translator

_BUBBLE_WIDTH = 380
_PREVIEW_MAX = 240


class PromptBubble(QWidget):
    confirmed = Signal(str)
    image_confirmed = Signal()
    rejected = Signal()

    def __init__(
        self, config: Config, translator: Translator, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._translator = translator
        self._text = ""
        self._is_image = False
        self._elapsed_ms = 0
        self._countdown_ms = 0
        self._setup_window()
        self._build_ui()
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_tick)
        self._translator.language_changed.connect(self._update_content)

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(_BUBBLE_WIDTH)
        self._animation = QPropertyAnimation(self, b"geometry", self)
        self._animation.setDuration(220)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(8)
        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet("color:#F8FAFC;font-size:11pt;font-weight:600;")
        close_button = QPushButton("×")
        close_button.setAccessibleName(self._translator.text("action.cancel"))
        close_button.setFixedSize(30, 30)
        close_button.setStyleSheet("color:#E2E8F0;background:transparent;border:0;")
        close_button.clicked.connect(self._cancel)
        header.addWidget(self._title)
        header.addStretch()
        header.addWidget(close_button)
        root.addLayout(header)

        self._preview = QLabel()
        self._preview.setWordWrap(True)
        self._preview.setStyleSheet("color:#E2E8F0;")
        root.addWidget(self._preview)
        self._characters = QLabel()
        self._characters.setStyleSheet("color:#94A3B8;")
        root.addWidget(self._characters)

        progress_row = QHBoxLayout()
        self._progress = QProgressBar()
        self._progress.setRange(0, 1_000)
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(4)
        self._remaining = QLabel()
        self._remaining.setStyleSheet("color:#94A3B8;")
        progress_row.addWidget(self._progress)
        progress_row.addWidget(self._remaining)
        root.addLayout(progress_row)

        buttons = QHBoxLayout()
        self._cancel_button = QPushButton()
        self._cancel_button.clicked.connect(self._cancel)
        self._confirm_button = QPushButton()
        self._confirm_button.setDefault(True)
        self._confirm_button.clicked.connect(self._confirm)
        buttons.addStretch()
        buttons.addWidget(self._cancel_button)
        buttons.addWidget(self._confirm_button)
        root.addLayout(buttons)

    def show_for_text(self, text: str, dock: QWidget) -> None:
        self._is_image = False
        self._text = text
        self._show_near(dock)

    def show_for_image(self, dock: QWidget) -> None:
        self._is_image = True
        self._text = ""
        self._show_near(dock)

    def _show_near(self, dock: QWidget) -> None:
        self._update_content()
        self.adjustSize()
        height = self.sizeHint().height()
        self._position_near(dock, height)
        self._countdown_ms = self._config.bubble_timeout_ms
        self._elapsed_ms = 0
        self._progress.setValue(0)
        self._remaining.setText(f"{self._countdown_ms // 1_000}s")
        self._timer.start()
        end = QRect(self.x(), self.y(), _BUBBLE_WIDTH, height)
        offset = -24 if self.x() < dock.x() else 24
        start = QRect(self.x() + offset, self.y(), _BUBBLE_WIDTH, height)
        self.setGeometry(start)
        self.show()
        self.raise_()
        self.activateWindow()
        self._animation.setStartValue(start)
        self._animation.setEndValue(end)
        self._animation.start()

    def _update_content(self) -> None:
        tr = self._translator.text
        self._cancel_button.setText(tr("action.cancel"))
        if self._is_image:
            self._title.setText(tr("ocr.confirm"))
            self._preview.setText(tr("prompt.image_description"))
            self._characters.clear()
            self._confirm_button.setText(tr("prompt.image_confirm"))
        else:
            self._title.setText(tr("prompt.read_question"))
            preview = self._text[:_PREVIEW_MAX]
            self._preview.setText(preview + ("…" if len(self._text) > _PREVIEW_MAX else ""))
            self._characters.setText(tr("prompt.characters", count=len(self._text)))
            self._confirm_button.setText(tr("prompt.confirm"))

    def _position_near(self, dock: QWidget, height: int) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        dock_geometry = dock.geometry()
        x = dock_geometry.left() - _BUBBLE_WIDTH - 8
        if dock_geometry.center().x() < screen.center().x():
            x = dock_geometry.right() + 8
        y = dock_geometry.center().y() - height // 2
        self.move(
            max(screen.left() + 4, min(x, screen.right() - _BUBBLE_WIDTH - 4)),
            max(screen.top() + 4, min(y, screen.bottom() - height - 4)),
        )

    def _on_tick(self) -> None:
        self._elapsed_ms += self._timer.interval()
        ratio = min(1.0, self._elapsed_ms / self._countdown_ms)
        self._progress.setValue(int(ratio * 1_000))
        remaining = max(0, (self._countdown_ms - self._elapsed_ms + 999) // 1_000)
        self._remaining.setText(f"{remaining}s")
        if self._elapsed_ms >= self._countdown_ms:
            self._cancel()

    def _confirm(self) -> None:
        self._timer.stop()
        self.hide()
        if self._is_image:
            self.image_confirmed.emit()
        else:
            self.confirmed.emit(self._text)

    def _cancel(self) -> None:
        self._timer.stop()
        self.hide()
        self.rejected.emit()

    def paintEvent(self, _event: object) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 10, 10)
        painter.setPen(QPen(QColor(71, 85, 105), 1))
        painter.fillPath(path, QColor(15, 23, 42, 245))
        painter.drawPath(path)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._confirm()
        elif event.key() == Qt.Key.Key_Escape:
            self._cancel()
        else:
            super().keyPressEvent(event)
