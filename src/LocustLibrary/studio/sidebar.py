"""Sidebar: open a load suite and show its user classes and their tasks."""

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from LocustLibrary.suiteplan import read_suite


class Sidebar(QWidget):  # type: ignore[misc]
    suite_opened = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._classes: list[Any] = []
        self.setObjectName("pane")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        open_btn = QPushButton("Open suite...")
        open_btn.setObjectName("ghost")
        open_btn.setAccessibleName("Open a load suite")
        open_btn.setToolTip("Open a .robot load suite (Ctrl+O)")
        open_btn.clicked.connect(self.choose_suite)
        lay.addWidget(open_btn)
        self.suite_label = QLabel("No suite open. Tasks from the Build tab run instead.")
        self.suite_label.setWordWrap(True)
        lay.addWidget(self.suite_label)
        lay.addWidget(_section("User classes"))
        self.class_list = QListWidget()
        self.class_list.setAccessibleName("User classes")
        self.class_list.currentRowChanged.connect(self._show_class_tasks)
        lay.addWidget(self.class_list)
        lay.addWidget(_section("Tasks of the selected class"))
        self.class_tasks = QListWidget()
        self.class_tasks.setAccessibleName("Class tasks")
        lay.addWidget(self.class_tasks)

    def choose_suite(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Open load suite", "", "Robot suites (*.robot)")
        if path:
            self.open_suite(path)

    def open_suite(self, path: str) -> None:
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            plan = read_suite(path)
        finally:
            QApplication.restoreOverrideCursor()
        self._classes = plan.classes
        rules = "".join(f"\nStop when {rule}" for rule in plan.stop_rules)
        self.suite_label.setText(f"{Path(path).name}\nHost: {plan.host or 'not set'}{rules}")
        self.suite_label.setToolTip(path)
        self.class_list.clear()
        for planned in plan.classes:
            detail = "  ".join(x for x in (planned.size, planned.wait and f"wait {planned.wait}",
                                           planned.pacing and f"pacing {planned.pacing}") if x)
            # The sidebar is narrow; details on their own line stay readable instead of cut.
            self.class_list.addItem(f"{planned.name}\n{detail}".strip())
        if plan.classes:
            self.class_list.setCurrentRow(0)
        self.suite_opened.emit(path)

    def _show_class_tasks(self, row: int) -> None:
        self.class_tasks.clear()
        if 0 <= row < len(self._classes):
            self.class_tasks.addItems(self._classes[row].tasks)


def _section(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("label")
    return label
