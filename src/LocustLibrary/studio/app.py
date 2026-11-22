"""Main studio application window."""

import sys
from typing import Any

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QKeySequence, QResizeEvent, QShortcut, QTextCursor
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QMainWindow,
        QSplitter,
        QStackedWidget,
        QTabBar,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PySide6 required for studio") from exc

from .build_tab import BuildTab
from .fonts import load_fonts
from .panels import set_table_colors
from .report_tab import ReportTab
from .run_tab import RunTab
from .sidebar import Sidebar
from .themes import THEMES, get_theme


class MainWindow(QMainWindow):  # type: ignore[misc, unused-ignore]
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("robotframework-locust studio")
        self.resize(1440, 900)
        self.setMinimumSize(900, 600)
        load_fonts()
        self._theme_name = "graphite"
        self.build_tab = BuildTab()
        self.run_tab = RunTab(self.build_tab.scenario)
        self.report_tab = ReportTab()
        self.sidebar = Sidebar()
        self.pages = QStackedWidget()
        self.tabs = QTabBar()
        self.tabs.setDrawBase(False)
        self.tabs.setAccessibleName("Sections")
        for page, title in ((self.build_tab, "Build"), (self.run_tab, "Run"),
                            (self.report_tab, "Report"), (self._make_settings_tab(), "Settings")):
            self.pages.addWidget(page)
            self.tabs.addTab(title)
        self.tabs.currentChanged.connect(self.pages.setCurrentIndex)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.pages)
        splitter.addWidget(self._make_right_panel())
        splitter.setSizes([210, 1000, 260])
        central = QWidget()
        lay = QVBoxLayout(central)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(self._make_header())
        lay.addWidget(splitter, 1)
        self.setCentralWidget(central)
        self._connect()
        self.apply_theme(self._theme_name)

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
        theme = get_theme(name)
        self.setStyleSheet(theme["qss"])
        for table in (self.run_tab.stats_table, self.report_tab.table):
            set_table_colors(table, theme["colors"])
        self.run_tab.charts.set_colors(theme["colors"])

    def _make_header(self) -> Any:
        header = QWidget()
        header.setObjectName("header")
        row = QHBoxLayout(header)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)
        name = QLabel("Locust Studio")
        name.setObjectName("title")
        track = QWidget()
        track.setObjectName("track")
        track_row = QHBoxLayout(track)
        track_row.setContentsMargins(2, 2, 2, 2)
        track_row.addWidget(self.tabs)
        for widget in (name, track):
            row.addWidget(widget)
        row.addStretch(1)
        for widget in (self.run_tab.status_label, self.run_tab.stop_btn, self.run_tab.run_btn):
            row.addWidget(widget)
        return header

    def _toggle_rtl(self, checked: bool) -> None:
        QApplication.setLayoutDirection(
            Qt.LayoutDirection.RightToLeft if checked else Qt.LayoutDirection.LeftToRight
        )

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            self.sidebar.setVisible(self.width() >= 1000)

    def _make_right_panel(self) -> Any:
        w = QWidget()
        w.setObjectName("pane")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 12, 12, 12)
        title = QLabel("Live log")
        title.setObjectName("label")
        lay.addWidget(title)
        self.log_text = QTextEdit()
        self.log_text.setObjectName("console")
        self.log_text.setReadOnly(True)
        self.log_text.setAccessibleName("Live log")
        self.log_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        lay.addWidget(self.log_text)
        return w

    def _append_log(self, text: str) -> None:
        self.log_text.moveCursor(QTextCursor.MoveOperation.End)
        self.log_text.insertPlainText(text)
        self.log_text.ensureCursorVisible()
        self.log_text.horizontalScrollBar().setValue(0)

    def _make_settings_tab(self) -> Any:
        w = QWidget()
        lay = QVBoxLayout(w)
        form = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.setAccessibleName("Theme")
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
