"""Shared semantic design tokens and Qt widget stylesheet."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from PySide6.QtGui import QGuiApplication, QPalette


@dataclass(frozen=True, slots=True)
class Palette:
    surface: str
    surface_subtle: str
    text: str
    text_muted: str
    border: str
    accent: str
    accent_hover: str
    accent_text: str
    error: str
    success: str
    focus: str
    selection: str


LIGHT = Palette(
    surface="#FFFFFF",
    surface_subtle="#F5F7FA",
    text="#172033",
    text_muted="#536079",
    border="#C9D1DF",
    accent="#2563EB",
    accent_hover="#1D4ED8",
    accent_text="#FFFFFF",
    error="#B42318",
    success="#067647",
    focus="#2563EB",
    selection="#EAF1FF",
)

DARK = Palette(
    surface="#111827",
    surface_subtle="#1F2937",
    text="#F3F4F6",
    text_muted="#A8B1C0",
    border="#4B5563",
    accent="#60A5FA",
    accent_hover="#3B82F6",
    accent_text="#0B1220",
    error="#FDA29B",
    success="#6CE9A6",
    focus="#60A5FA",
    selection="#243B5A",
)


def palette_for_theme(theme: str, application: QGuiApplication | None = None) -> Palette:
    if theme == "dark":
        return DARK
    if theme == "light":
        return LIGHT
    selected_application = application or cast(QGuiApplication | None, QGuiApplication.instance())
    if selected_application is not None:
        window = selected_application.palette().color(QPalette.ColorRole.Window)
        if window.lightness() < 128:
            return DARK
    return LIGHT


def application_stylesheet(palette: Palette = LIGHT) -> str:
    """Return one consistent, keyboard-accessible widget stylesheet."""
    return f"""
        QDialog, QWidget {{
            background: {palette.surface};
            color: {palette.text};
            font-size: 10pt;
        }}
        QLabel[muted="true"] {{ color: {palette.text_muted}; }}
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
            min-height: 28px;
            padding: 2px 8px;
            border: 1px solid {palette.border};
            border-radius: 5px;
            background: {palette.surface};
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
        QListWidget:focus, QPushButton:focus {{
            border: 2px solid {palette.focus};
        }}
        QPushButton {{
            min-height: 30px;
            padding: 2px 12px;
            border: 1px solid {palette.border};
            border-radius: 5px;
            background: {palette.surface_subtle};
        }}
        QPushButton:hover {{ border-color: {palette.accent}; }}
        QPushButton[primary="true"] {{
            color: {palette.accent_text};
            background: {palette.accent};
            border-color: {palette.accent};
        }}
        QPushButton[primary="true"]:hover {{ background: {palette.accent_hover}; }}
        QPushButton:disabled {{ color: {palette.text_muted}; }}
        QListWidget {{
            background: {palette.surface_subtle};
            border: 0;
            border-right: 1px solid {palette.border};
            padding: 8px;
        }}
        QListWidget::item {{ padding: 9px 12px; border-radius: 5px; }}
        QListWidget::item:selected {{ color: {palette.accent}; background: {palette.selection}; }}
        QMenu {{
            background: {palette.surface};
            border: 1px solid {palette.border};
            padding: 5px;
        }}
        QMenu::item {{ padding: 7px 22px; border-radius: 4px; }}
        QMenu::item:selected {{ color: {palette.accent}; background: {palette.selection}; }}
        QLabel[result="success"] {{ color: {palette.success}; font-weight: 600; }}
        QLabel[result="error"] {{ color: {palette.error}; font-weight: 600; }}
        QToolTip {{
            color: {palette.text};
            background: {palette.surface};
            border: 1px solid {palette.border};
        }}
    """


def stylesheet_for_theme(theme: str, application: QGuiApplication | None = None) -> str:
    return application_stylesheet(palette_for_theme(theme, application))
