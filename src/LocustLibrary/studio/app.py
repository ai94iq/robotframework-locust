"""Main studio application window."""

import sys
from typing import Any

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeySequence, QShortcut, QTextCursor
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFormLayout,
        QLabel,
        QMainWindow,
        QSplitter,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PySide6 required for studio") from exc

from .build_tab import BuildTab
from .report_tab import ReportTab
from .run_tab import RunTab
from .sidebar import Sidebar
from .themes import THEMES, get_theme


class MainWindow(QMainWindow):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("robotframework-locust studio")
        self.resize(1440, 900)
        self.setMinimumSize(900, 600)
        self._theme_name = "dark_console"
        self.build_tab = BuildTab()
        self.run_tab = RunTab(self.build_tab.scenario)
        self.report_tab = ReportTab()
        self.sidebar = Sidebar()
        self.tabs = QTabWidget()
        self.tabs.addTab(self.build_tab, "Build")
        self.tabs.addTab(self.run_tab, "Run")
        self.tabs.addTab(self.report_tab, "Report")
        self.tabs.addTab(self._make_settings_tab(), "Settings")
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self._make_right_panel())
        splitter.setSizes([260, 880, 300])
        self.setCentralWidget(splitter)
        self._connect()

    def _connect(self) -> None:
        self.sidebar.suite_opened.connect(self.run_tab.set_suite)
        self.run_tab.console.connect(self._append_log)
        self.run_tab.final.connect(self.report_tab.show_final)
        self.run_tab.outputs.connect(self.report_tab.set_outputs)
        for keys, action in (("Ctrl+R", self.run_tab.run), ("Ctrl+O", self.sidebar.choose_suite),
                             ("Ctrl+,", lambda: self.tabs.setCurrentIndex(3))):
            QShortcut(QKeySequence(keys), self).activated.connect(action)

    def apply_theme(self, name: str) -> None:
        self._theme_name = name
        self.setStyleSheet(get_theme(name)["qss"])

    def _toggle_rtl(self, checked: bool) -> None:
        QApplication.instance().setLayoutDirection(
            Qt.RightToLeft if checked else Qt.LeftToRight
        )

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            self.sidebar.setVisible(self.width() >= 1000)

    def _make_right_panel(self) -> Any:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Live log"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setAccessibleName("Live log")
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        lay.addWidget(self.log_text)
        return w

    def _append_log(self, text: str) -> None:
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertPlainText(text)
        self.log_text.ensureCursorVisible()
        self.log_text.horizontalScrollBar().setValue(0)

    def _make_settings_tab(self) -> Any:
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QFormLayout()
        self.theme_combo = QComboBox()
        for k, v in THEMES.items():
            self.theme_combo.addItem(v["name"], k)
        self.theme_combo.currentIndexChanged.connect(
            lambda: self.apply_theme(self.theme_combo.currentData())
        )
        form.addRow("Theme", self.theme_combo)
        self.rtl_check = QCheckBox("Right-to-left layout")
        self.rtl_check.toggled.connect(self._toggle_rtl)
        form.addRow(self.rtl_check)
        lay.addLayout(form)
        lay.addStretch()
        return w


def main() -> None:
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
