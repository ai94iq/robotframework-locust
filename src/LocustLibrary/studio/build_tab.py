"""Build tab: HTTP tasks put together by hand, run when no suite is open."""

from typing import Any

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class BuildTab(QWidget):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[dict[str, Any]] = []
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        form = QFormLayout()
        self.host_edit = QLineEdit("http://127.0.0.1:8765")
        self.host_edit.setAccessibleName("Host URL")
        self.wait_min_edit = QLineEdit("0.1s")
        self.wait_max_edit = QLineEdit("0.5s")
        form.addRow("Host", self.host_edit)
        form.addRow("Wait min", self.wait_min_edit)
        form.addRow("Wait max", self.wait_max_edit)
        lay.addLayout(form)
        self.task_list = QListWidget()
        self.task_list.setAccessibleName("Task list")
        lay.addWidget(QLabel("Tasks"))
        self.empty_tasks_label = QLabel("No tasks yet. Add one below.")
        lay.addWidget(self.empty_tasks_label)
        lay.addWidget(self.task_list)
        lay.addLayout(self._task_row())

    def _task_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.task_name = QLineEdit("Get Home")
        self.task_name.setAccessibleName("Task name")
        self.task_path = QLineEdit("/")
        self.task_path.setAccessibleName("Task path")
        self.task_method = QComboBox()
        self.task_method.addItems(["GET", "POST"])
        self.task_weight = QSpinBox()
        self.task_weight.setValue(1)
        add_btn = QPushButton("Add task")
        add_btn.setAccessibleName("Add task")
        add_btn.clicked.connect(self._add_task)
        for widget in (self.task_name, self.task_method, self.task_path, QLabel("w"), self.task_weight,
                       add_btn):
            row.addWidget(widget)
        return row

    def _add_task(self) -> None:
        t = {
            "name": self.task_name.text(),
            "method": self.task_method.currentText(),
            "path": self.task_path.text(),
            "weight": self.task_weight.value(),
        }
        self.tasks.append(t)
        self.task_list.addItem(f"{t['method']} {t['path']} (w{t['weight']}) - {t['name']}")
        self.empty_tasks_label.hide()

    def scenario(self) -> dict[str, Any]:
        return {"host": self.host_edit.text(), "wait_min": self.wait_min_edit.text(),
                "wait_max": self.wait_max_edit.text(), "tasks": list(self.tasks)}
