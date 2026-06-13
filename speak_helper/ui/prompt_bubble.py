"""询问气泡：复制文字后弹出，让用户确认是否朗读
- 无边框、始终置顶、从 Dock 方向滑入
- 6s 倒计时自动关闭
- 支持键盘快捷键：Enter 确认、Esc 取消
"""
from __future__ import annotations

from PySide6.QtCore import (
    QEasingCurve, QPoint, QPropertyAnimation, QRect, QTimer, Qt, Signal,
)
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QProgressBar,
    QPushButton, QVBoxLayout, QWidget,
)

from ..config import Config

_BUBBLE_W = 330
_PREVIEW_MAX = 120      # 预览最多显示字符数


class PromptBubble(QWidget):
    confirmed = Signal(str)       # 文字确认朗读
    image_confirmed = Signal()    # 图片确认 OCR + 朗读
    rejected = Signal()

    def __init__(self, config: Config, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._config = config
        self._text = ""
        self._is_image = False      # 当前是否为图片 OCR 模式
        self._countdown_ms = 0
        self._elapsed_ms = 0

        self._setup_window()
        self._build_ui()
        self._setup_timers()

    # ── public API ────────────────────────────────────────────────────────────

    def show_for_text(self, text: str, dock: QWidget) -> None:
        self._is_image = False
        self._text = text
        self._update_content()
        self._show_near(dock)

    def show_for_image(self, dock: QWidget) -> None:
        self._is_image = True
        self._text = ""
        self._update_content()
        self._show_near(dock)

    def _show_near(self, dock: QWidget) -> None:
        """定位、重置倒计时、滑入动画。"""
        # 先让布局根据内容计算出真实高度
        self.adjustSize()
        h = self.sizeHint().height()

        self._position_near(dock, h)
        self._countdown_ms = self._config.bubble_timeout_ms
        self._elapsed_ms = 0
        self._prog.setValue(0)
        self._time_label.setText(f"{self._countdown_ms // 1000}s")
        self._timer.start(100)

        start_rect = QRect(self._slide_start_x(), self.y(), _BUBBLE_W, h)
        end_rect   = QRect(self.x(),              self.y(), _BUBBLE_W, h)
        self.setGeometry(start_rect)
        self.show()
        self.raise_()
        self.activateWindow()
        self._slide_anim.setStartValue(start_rect)
        self._slide_anim.setEndValue(end_rect)
        self._slide_anim.start()

    # ── setup ─────────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            # 不用 Tool：Tool 在 Windows 上不抢焦点，导致按钮无法点击
            # 用 Dialog 代替：不出现在任务栏，且能正常接收鼠标/键盘事件
            | Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(_BUBBLE_W)   # 仅固定宽度，高度由内容自适应

        self._slide_anim = QPropertyAnimation(self, b"geometry", self)
        self._slide_anim.setDuration(220)
        self._slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 10, 12, 10)
        outer.setSpacing(6)

        # ── 标题行 ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        self._title_label = QLabel("🔊  朗读这段文字？")
        self._title_label.setStyleSheet("color:#E5E7EB; font-weight:600; font-size:13px;")
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(20, 20)
        close_btn.setStyleSheet(
            "QPushButton{color:#9CA3AF;background:transparent;border:none;font-size:14px;}"
            "QPushButton:hover{color:#F9FAFB;}"
        )
        close_btn.clicked.connect(self._on_cancel)
        header.addWidget(self._title_label)
        header.addStretch()
        header.addWidget(close_btn)
        outer.addLayout(header)

        # 分隔线（用 paintEvent 画，这里只占位）
        outer.addSpacing(2)

        # ── 预览文字 ─────────────────────────────────────────────────────────
        self._preview_label = QLabel()
        self._preview_label.setWordWrap(True)
        self._preview_label.setStyleSheet("color:#D1D5DB; font-size:12px; line-height:1.4;")
        outer.addWidget(self._preview_label)

        # 字数信息
        self._char_label = QLabel()
        self._char_label.setStyleSheet("color:#6B7280; font-size:11px;")
        outer.addWidget(self._char_label)

        # ── 倒计时行 ─────────────────────────────────────────────────────────
        ct_row = QHBoxLayout()
        self._prog = QProgressBar()
        self._prog.setRange(0, 1000)
        self._prog.setValue(0)
        self._prog.setTextVisible(False)
        self._prog.setFixedHeight(4)
        self._prog.setStyleSheet(
            "QProgressBar{background:#374151;border-radius:2px;}"
            "QProgressBar::chunk{background:#3B82F6;border-radius:2px;}"
        )
        self._time_label = QLabel("6s")
        self._time_label.setStyleSheet("color:#6B7280; font-size:11px;")
        self._time_label.setFixedWidth(24)
        ct_row.addWidget(self._prog)
        ct_row.addWidget(self._time_label)
        outer.addLayout(ct_row)

        # ── 按钮行 ───────────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        cancel_btn = QPushButton("取消  Esc")
        cancel_btn.setStyleSheet(
            "QPushButton{color:#9CA3AF;background:transparent;border:1px solid #4B5563;"
            "border-radius:6px;padding:5px 14px;font-size:12px;}"
            "QPushButton:hover{border-color:#6B7280;color:#D1D5DB;}"
        )
        cancel_btn.clicked.connect(self._on_cancel)

        self._confirm_btn = QPushButton("🔊  朗读  ↵")
        self._confirm_btn.setStyleSheet(
            "QPushButton{color:#FFFFFF;background:#3B82F6;border:none;"
            "border-radius:6px;padding:5px 14px;font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:#2563EB;}"
            "QPushButton:pressed{background:#1D4ED8;}"
        )
        self._confirm_btn.clicked.connect(self._on_confirm)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._confirm_btn)
        outer.addLayout(btn_row)

    def _setup_timers(self) -> None:
        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_tick)

    # ── painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        painter.setPen(QPen(QColor(75, 85, 99, 160), 1.0))
        painter.fillPath(path, QColor(26, 26, 36, 232))
        painter.drawPath(path)

    # ── logic ─────────────────────────────────────────────────────────────────

    def _update_content(self) -> None:
        if self._is_image:
            self._title_label.setText("🖼️  识别图片文字并朗读？")
            self._preview_label.setText("将调用 OCR API 提取图片中的文字，然后朗读。")
            self._char_label.setText("")
            self._confirm_btn.setText("🔍  识别并朗读  ↵")
        else:
            self._title_label.setText("🔊  朗读这段文字？")
            preview = self._text[:_PREVIEW_MAX]
            if len(self._text) > _PREVIEW_MAX:
                preview += "…"
            self._preview_label.setText(preview)
            self._char_label.setText(f"共 {len(self._text)} 字")
            self._confirm_btn.setText("🔊  朗读  ↵")

    def _position_near(self, dock: QWidget, h: int) -> None:
        dock_geo = dock.geometry()
        screen = QApplication.primaryScreen().availableGeometry()

        x = dock_geo.left() - _BUBBLE_W - 8
        y = dock_geo.top() + dock_geo.height() // 2 - h // 2

        if dock_geo.center().x() < screen.center().x():
            x = dock_geo.right() + 8

        x = max(screen.left() + 4, min(x, screen.right() - _BUBBLE_W - 4))
        y = max(screen.top() + 4,  min(y, screen.bottom() - h - 4))
        self.move(x, y)

    def _slide_start_x(self) -> int:
        screen = QApplication.primaryScreen().availableGeometry()
        if self.x() + _BUBBLE_W // 2 < screen.center().x():
            return self.x() - 30
        return self.x() + 30

    def _on_tick(self) -> None:
        self._elapsed_ms += 100
        ratio = min(1.0, self._elapsed_ms / self._countdown_ms)
        self._prog.setValue(int(ratio * 1000))
        remaining = max(0, (self._countdown_ms - self._elapsed_ms) // 1000)
        self._time_label.setText(f"{remaining}s")
        if self._elapsed_ms >= self._countdown_ms:
            self._on_cancel()

    def _on_confirm(self) -> None:
        self._timer.stop()
        self.hide()
        if self._is_image:
            self.image_confirmed.emit()
        else:
            self.confirmed.emit(self._text)

    def _on_cancel(self) -> None:
        self._timer.stop()
        self.hide()
        self.rejected.emit()

    # ── keyboard ──────────────────────────────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_confirm()
        elif event.key() == Qt.Key.Key_Escape:
            self._on_cancel()
        else:
            # 任意按键暂停倒计时
            self._timer.stop()
