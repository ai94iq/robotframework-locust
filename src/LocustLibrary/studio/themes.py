"""Theme definitions for the studio GUI."""

from typing import Any

THEMES: dict[str, dict[str, Any]] = {
    "dark_console": {
        "name": "Dark Console",
        "qss": """
        QWidget { background: #1a1a1d; color: #f4f4f5; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
        * { color: #f4f4f5; }
        QMainWindow { background: #1a1a1d; }
        QTabWidget::pane { border: 1px solid #2a2a2e; background: #1a1a1d; }
        QTabBar::tab { background: #141416; color: #a1a1aa; padding: 8px 16px; border: 1px solid #2a2a2e; }
        QTabBar::tab:selected { background: #2563eb; color: #fff; }
        QFrame { border-radius: 8px; }
        QWidget#panel { background: #1f1f23; border: 1px solid #2a2a2e; border-radius: 12px; padding: 16px; }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #2563eb; outline: none; }
        QPushButton:focus { outline: 2px solid #2563eb; outline-offset: 2px; }
        QPushButton:hover { background: #1d4ed8; }
        QPushButton#danger { background: #dc2626; }
        QPushButton#ghost { background: transparent; border: 1px solid #2a2a2e; color: #e4e4e7; }
        QLineEdit, QSpinBox, QDoubleSpinBox { background: #141416; border: 1px solid #2a2a2e; color: #e4e4e7; padding: 6px 8px; border-radius: 4px; }
        QTableWidget { background: #141416; gridline-color: #2a2a2e; }
        QHeaderView::section { background: #1f1f23; color: #71717a; padding: 6px; border: none; font-size: 10px; text-transform: uppercase; }
        QListWidget { background: #141416; border: 1px solid #2a2a2e; }
        QListWidget::item:selected { background: #1f1f23; border-left: 2px solid #2563eb; }
        QStatusBar { background: #111113; color: #a1a1aa; }
        """,
    },
    "clean_light": {
        "name": "Clean Light",
        "qss": """
        QWidget { background: #fafafa; color: #18181b; font-family: 'Segoe UI', sans-serif; font-size: 13px; }
        QMainWindow { background: #fafafa; }
        QTabWidget::pane { border: 1px solid #e4e4e7; background: #fafafa; border-radius: 8px; }
        QTabBar::tab { background: #f4f4f5; color: #71717a; padding: 8px 16px; border-radius: 6px; margin: 2px; }
        QTabBar::tab:selected { background: #fff; color: #18181b; }
        QPushButton { background: #18181b; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-weight: 500; }
        QPushButton:hover { background: #27272a; }
        QPushButton#danger { background: #dc2626; }
        QPushButton#ghost { background: transparent; border: 1px solid #e4e4e7; color: #18181b; }
        QLineEdit, QSpinBox, QDoubleSpinBox { background: #fafafa; border: 1px solid #e4e4e7; color: #18181b; padding: 8px 10px; border-radius: 8px; }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #18181b; outline: none; }
        QPushButton:focus { outline: 2px solid #18181b; outline-offset: 2px; }
        QTableWidget { background: #fff; gridline-color: #f4f4f5; }
        QHeaderView::section { background: #f4f4f5; color: #a1a1aa; padding: 8px; border: none; font-size: 10px; text-transform: uppercase; }
        QListWidget { background: #fff; border: 1px solid #e4e4e7; border-radius: 8px; }
        QListWidget::item:selected { background: #f4f4f5; }
        QStatusBar { background: #fff; color: #71717a; border-top: 1px solid #e4e4e7; }
        """,
    },
    "neon_dark": {
        "name": "Neon Dark",
        "qss": """
        QWidget { background: #05050a; color: #ffffff; font-family: 'Consolas', monospace; font-size: 12px; }
        * { color: #ffffff; }
        QMainWindow { background: #05050a; }
        QTabWidget::pane { border: 1px solid #1a1a2e; background: #05050a; }
        QTabBar::tab { background: #0a0a14; color: #888; padding: 8px 16px; border: 1px solid #1a1a2e; }
        QTabBar::tab:selected { background: #00ffff; color: #05050a; }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #00ffff; outline: none; }
        QPushButton:focus { outline: 2px solid #00ffff; outline-offset: 2px; }
        QPushButton:hover { background: #00e6e6; }
        QPushButton#danger { background: #ff0066; color: #fff; }
        QPushButton#ghost { background: transparent; border: 1px solid #1a1a2e; color: #00ffff; }
        QLineEdit, QSpinBox, QDoubleSpinBox { background: #0a0a14; border: 1px solid #1a1a2e; color: #00ffff; padding: 6px 8px; border-radius: 4px; }
        QTableWidget { background: #0a0a14; gridline-color: #1a1a2e; }
        QHeaderView::section { background: #0a0a14; color: #00ffff; padding: 6px; border: none; font-size: 9px; text-transform: uppercase; }
        QListWidget { background: #0a0a14; border: 1px solid #1a1a2e; }
        QListWidget::item:selected { background: #1a1a2e; color: #00ffff; border-left: 2px solid #00ffff; }
        QStatusBar { background: #0a0a14; color: #888; }
        """,
    },
    "high_contrast": {
        "name": "High Contrast",
        "qss": """
        QWidget { background: #000000; color: #ffffff; font-family: 'Segoe UI', sans-serif; font-size: 14px; }
        QMainWindow { background: #000000; }
        QPushButton { background: #ffff00; color: #000000; border: 2px solid #ffffff; padding: 8px 16px; border-radius: 4px; font-weight: 700; }
        QPushButton:focus { outline: 3px solid #00ffff; outline-offset: 2px; }
        QLineEdit, QSpinBox, QDoubleSpinBox { background: #000000; border: 2px solid #ffffff; color: #ffffff; padding: 8px 10px; border-radius: 4px; }
        QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 3px solid #ffff00; }
        QTableWidget { background: #000000; gridline-color: #ffffff; }
        QHeaderView::section { background: #000000; color: #ffff00; padding: 6px; border: 2px solid #ffffff; font-size: 11px; text-transform: uppercase; }
        QListWidget { background: #000000; border: 2px solid #ffffff; }
        QListWidget::item:selected { background: #ffff00; color: #000000; }
        QTabBar::tab { background: #000000; color: #ffffff; border: 2px solid #ffffff; padding: 8px 16px; }
        QTabBar::tab:selected { background: #ffff00; color: #000000; }
        QStatusBar { background: #000000; color: #ffffff; border-top: 2px solid #ffffff; }
        """,
    },
}


def get_theme(name: str) -> dict[str, Any]:
    return THEMES.get(name, THEMES["dark_console"])
