"""Graphite (dark, default) and Paper (light): one structure, two palettes, per DESIGN.md."""

from string import Template
from typing import Any

# Tone steps window, panel, raised separate areas; line only sits between panes, rows and inputs.
_GRAPHITE = {"window": "#151518", "panel": "#1c1c20", "raised": "#232328", "line": "#2c2c32",
             "ink": "#ececef", "muted": "#8d8d96", "accent": "#5865f2", "accent_hover": "#4049b8",
             "focus": "#7c8cff", "second": "#c4a1ff", "pass": "#3ecf8e", "fail": "#f2555a"}
_PAPER = {"window": "#f7f5f0", "panel": "#fffdf9", "raised": "#efece5", "line": "#e2ddd2",
          "ink": "#1d1b18", "muted": "#6f6a61", "accent": "#0b7476", "accent_hover": "#0a5a5b",
          "focus": "#0b7476", "second": "#c2551f", "pass": "#16804a", "fail": "#d23c3c"}

UI_FONT = "'Inter', 'Segoe UI', sans-serif"
MONO_FONT = "'JetBrains Mono', 'Consolas', monospace"

_QSS = Template("""
QWidget { background: $window; color: $ink; font-family: $ui; font-size: 13px; }
QLabel, QCheckBox { background: transparent; }
QWidget#pane, QWidget#header { background: $panel; }
QWidget#header { border-bottom: 1px solid $line; }
QWidget#track { background: $raised; border-radius: 8px; }
QSplitter::handle { background: $line; }
QTabBar { background: transparent; }
QLabel#title { font-size: 14px; font-weight: 500; }
QLabel#headline { font-size: 18px; font-weight: 600; }
QTabBar::tab { background: $raised; color: $muted; border: 2px solid $raised; border-radius: 6px;
    padding: 4px 12px; }
QTabBar::tab:hover { color: $ink; }
QTabBar::tab:selected { background: $window; color: $ink; }
QPushButton { background: $accent; color: #ffffff; border: 2px solid $accent; border-radius: 6px;
    padding: 4px 12px; font-weight: 500; }
QPushButton:hover { background: $accent_hover; border-color: $accent_hover; }
QPushButton:focus { border-color: $focus; }
QPushButton:disabled { background: $raised; border-color: $raised; color: $muted; }
QPushButton#ghost { background: transparent; color: $ink; border: 1px solid $line; }
QPushButton#ghost:hover { background: $raised; }
QPushButton#ghost:focus { border: 2px solid $focus; }
QPushButton#ghost:disabled { background: transparent; border: 1px solid $line; color: $muted; }
QPushButton#danger { background: $fail; border-color: $fail; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit { background: $window; color: $ink;
    border: 1px solid $line; border-radius: 6px; padding: 5px 8px;
    selection-background-color: $accent; selection-color: #ffffff; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border: 2px solid $focus; }
QTextEdit#console { background: $panel; border: none; font-family: $mono; font-size: 12px; }
QListWidget { background: $panel; border: none; padding: 2px; }
QListWidget::item { padding: 4px 6px; border-radius: 6px; }
QListWidget::item:selected { background: $raised; color: $ink; }
QTableWidget { background: $panel; gridline-color: $line; border: 1px solid $line;
    border-radius: 8px; font-family: $mono; font-size: 12px; }
QTableWidget::item { padding: 2px 10px; }
QTableWidget::item:selected { background: $raised; color: $ink; }
QHeaderView::section { background: $panel; color: $muted; border: none;
    border-bottom: 1px solid $line; padding: 6px 10px; font-family: $ui; font-size: 11px;
    font-weight: 600; }
QLabel#label { color: $muted; font-size: 11px; font-weight: 600; }
QLabel#pill { background: $raised; color: $muted; border-radius: 11px; padding: 3px 10px;
    font-size: 11px; }
QLabel#pill[running="true"] { color: $pass; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 0; }
QScrollBar::handle { background: $line; border-radius: 5px; min-height: 24px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip { background: $raised; color: $ink; border: 1px solid $line; }
QStatusBar { background: $panel; color: $muted; }
""")


def _theme(name: str, colors: dict[str, str]) -> dict[str, Any]:
    return {"name": name, "colors": colors,
            "qss": _QSS.substitute(colors, ui=UI_FONT, mono=MONO_FONT)}


THEMES: dict[str, dict[str, Any]] = {
    "graphite": _theme("Graphite (dark)", _GRAPHITE),
    "paper": _theme("Paper (light)", _PAPER),
}


def get_theme(name: str) -> dict[str, Any]:
    return THEMES.get(name, THEMES["graphite"])
