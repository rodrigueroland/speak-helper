"""Draggable edge dock showing ready, speaking, paused, and error states."""

from __future__ import annotations

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPoint,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QWidget

from ..assets import ICON_ERROR, ICON_IDLE, ICON_PAUSED, ICON_SPEAKING
from ..config import Config
from ..i18n import Translator

_STATE_COLORS = {
    "idle": "#3B82F6",
    "speaking": "#10B981",
    "paused": "#888888",
    "error": "#EF4444",
}

_STATE_ICONS = {
    "idle": ICON_IDLE,
    "speaking": ICON_SPEAKING,
    "paused": ICON_PAUSED,
    "error": ICON_ERROR,
}

_DOCK_SIZE = 56  # Total widget size including shadow margin.
_CIRCLE_R = 22
_EDGE_GAP = 8


class FloatingDock(QWidget):
    clicked = Signal()
    double_clicked = Signal()
    right_clicked = Signal(QPoint)

    def __init__(
        self,
        config: Config,
        translator: Translator,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._config = config
        self._translator = translator
        self._state = "idle"
        self._pulse = 0.0
        self._drag_offset: QPoint | None = None
        self._is_dragging = False
        self._renderers: dict[str, QSvgRenderer] = {}

        self._setup_window()
        self._setup_animation()
        self._restore_position()
        self._translator.language_changed.connect(self._update_accessible_text)
        self._update_accessible_text()
        self.show()

    # ── public API ────────────────────────────────────────────────────────────

    def set_state(self, state: str) -> None:
        """state: 'idle' | 'speaking' | 'paused' | 'error'"""
        self._state = state
        if state == "speaking":
            self._anim.start()
        else:
            self._anim.stop()
            self._pulse = 0.0
        self.update()
        self._update_accessible_text()

    def _update_accessible_text(self) -> None:
        text = self._translator.text(f"status.{self._state}")
        self.setAccessibleName(text)
        self.setToolTip(text)

    # ── Qt property for animation ─────────────────────────────────────────────

    def _get_pulse(self) -> float:
        return self._pulse

    def _set_pulse(self, v: float) -> None:
        self._pulse = v
        self.update()

    pulse = Property(float, _get_pulse, _set_pulse)

    # ── setup ─────────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(QSize(_DOCK_SIZE, _DOCK_SIZE))
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

    def _setup_animation(self) -> None:
        self._anim = QPropertyAnimation(self, b"pulse", self)
        self._anim.setDuration(1400)
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.setLoopCount(-1)
        self._anim.setEasingCurve(QEasingCurve.Type.SineCurve)

    def _restore_position(self) -> None:
        saved_x = self._config.get("ui", "dock_x")
        saved_y = self._config.get("ui", "dock_y")
        if saved_x is not None and saved_y is not None:
            self.move(int(saved_x), int(saved_y))
        else:
            self._snap_to_default()

    def _snap_to_default(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        if self._config.dock_edge == "left":
            x = screen.left() + _EDGE_GAP
        else:
            x = screen.right() - _DOCK_SIZE - _EDGE_GAP
        y = screen.center().y() - _DOCK_SIZE // 2
        self.move(x, y)

    def _snap_to_edge(self) -> None:
        """Snap the dock to the closest horizontal screen edge."""
        screen = QApplication.primaryScreen().availableGeometry()
        cx = self.x() + _DOCK_SIZE // 2
        mid = screen.center().x()
        if cx < mid:
            x = screen.left() + _EDGE_GAP
            self._config.set("ui", "dock_edge", "left")
        else:
            x = screen.right() - _DOCK_SIZE - _EDGE_GAP
            self._config.set("ui", "dock_edge", "right")
        # Preserve vertical position while keeping the dock on screen.
        y = max(screen.top(), min(self.y(), screen.bottom() - _DOCK_SIZE))
        self.move(x, y)

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = _DOCK_SIZE // 2
        cy = _DOCK_SIZE // 2
        r = _CIRCLE_R
        border_color = QColor(_STATE_COLORS.get(self._state, "#3B82F6"))

        # Shadow.
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 45))
        painter.drawEllipse(QPointF(cx + 1.5, cy + 2.5), float(r), float(r))

        # Circular background.
        painter.setBrush(QColor(24, 24, 32, 225))
        painter.setPen(QPen(border_color, 2.0))
        painter.drawEllipse(QPointF(cx, cy), float(r), float(r))

        # Pulsing ring while speaking.
        if self._state == "speaking" and self._pulse > 0:
            alpha = int(220 * (1.0 - self._pulse))
            pulse_color = QColor(16, 185, 129, alpha)
            pulse_r = r + 4 + self._pulse * 7
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(pulse_color, 1.5))
            painter.drawEllipse(QPointF(cx, cy), pulse_r, pulse_r)

        # State icon.
        renderer = self._get_renderer(self._state)
        icon_size = 22
        renderer.render(
            painter,
            QRectF(cx - icon_size / 2, cy - icon_size / 2, icon_size, icon_size),
        )

    def _get_renderer(self, state: str) -> QSvgRenderer:
        if state not in self._renderers:
            r = QSvgRenderer(self)
            r.load(bytearray(_STATE_ICONS[state].encode()))
            self._renderers[state] = r
        return self._renderers[state]

    # ── mouse events ──────────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPos() - self.frameGeometry().topLeft()
            self._is_dragging = False
        elif event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(event.globalPos())

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_offset:
            self._is_dragging = True
            new_pos = event.globalPos() - self._drag_offset
            screen = QApplication.primaryScreen().availableGeometry()
            new_pos.setX(max(screen.left(), min(new_pos.x(), screen.right() - _DOCK_SIZE)))
            new_pos.setY(max(screen.top(), min(new_pos.y(), screen.bottom() - _DOCK_SIZE)))
            self.move(new_pos)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if self._is_dragging:
                self._snap_to_edge()
                self._config.set("ui", "dock_x", self.x())
                self._config.set("ui", "dock_y", self.y())
                self._config.save()
            else:
                self.clicked.emit()
            self._drag_offset = None
            self._is_dragging = False

    def mouseDoubleClickEvent(self, _event) -> None:
        self.double_clicked.emit()
