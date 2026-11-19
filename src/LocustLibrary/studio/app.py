"""Main studio application window."""

import sys
from typing import Any

try:
    from PySide6.QtCore import Qt, QThread, Signal
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDoubleSpinBox,
        QFormLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QListWidget,
        QMainWindow,
        QMessageBox,
        QProgressBar,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QTableWidget,
        QTableWidgetItem,
        QTabWidget,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit("PySide6 required for studio") from exc

from .themes import THEMES, get_theme


class RunWorker(QThread):  # type: ignore[misc]
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, scenario_kwargs: dict[str, Any]) -> None:
        super().__init__()
        self.kwargs = scenario_kwargs

    def run(self) -> None:
        try:
            from LocustLibrary import LocustLibrary

            lib = LocustLibrary()
            lib.create_load_test(self.kwargs["host"])
            lib.set_wait_time(self.kwargs["wait_min"], self.kwargs["wait_max"])
            for t in self.kwargs["tasks"]:
                if t["kind"] == "http":
                    if t["method"] == "GET":
                        lib.add_get_request(t["name"], t["path"], weight=t["weight"])
                    else:
                        lib.add_post_request(t["name"], t["path"], weight=t["weight"])
                else:
                    lib.add_task(t["name"], keyword=t.get("keyword", ""), weight=t["weight"])
            lib.run_load_test(
                users=self.kwargs["users"],
                spawn_rate=self.kwargs["spawn_rate"],
                run_time=self.kwargs["run_time"],
                csv_prefix=self.kwargs["csv_prefix"],
            )
            self.finished.emit(lib.get_locust_stats())
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class MainWindow(QMainWindow):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("robotframework-locust studio")
        self.resize(1440, 900)
        self.setMinimumSize(900, 600)
        self._theme_name = "dark_console"
        self._tasks: list[dict[str, Any]] = []
        self._worker: RunWorker | None = None

        self.tabs = QTabWidget()
        self._build_tab = self._make_build_tab()
        self._run_tab = self._make_run_tab()
        self._report_tab = self._make_report_tab()
        self._settings_tab = self._make_settings_tab()

        self.tabs.addTab(self._build_tab, "Build")
        self.tabs.addTab(self._run_tab, "Run")
        self.tabs.addTab(self._report_tab, "Report")
        self.tabs.addTab(self._settings_tab, "Settings")

        from PySide6.QtWidgets import QSplitter
        splitter = QSplitter(Qt.Horizontal)
        self.sidebar = self._make_sidebar()
        self.right_panel = self._make_right_panel()
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.tabs)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([220, 920, 280])
        self.setCentralWidget(splitter)

        self.setStatusBar(QStatusBar())
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.progress_bar)
        from PySide6.QtGui import QKeySequence, QShortcut

        sc_run = QShortcut(QKeySequence("Ctrl+R"), self)
        sc_run.activated.connect(self._run)
        sc_settings = QShortcut(QKeySequence("Ctrl+,"), self)
        sc_settings.activated.connect(lambda: self.tabs.setCurrentIndex(3))

    def apply_theme(self, name: str) -> None:
        self._theme_name = name
        self.setStyleSheet(get_theme(name)["qss"])

    def _toggle_rtl(self, checked: bool) -> None:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setLayoutDirection(
            Qt.RightToLeft if checked else Qt.LeftToRight
        )

    def resizeEvent(self, event: object) -> None:
        super().resizeEvent(event)
        if hasattr(self, "sidebar"):
            self.sidebar.setVisible(self.width() >= 1000)

    def _make_sidebar(self) -> Any:
        from PySide6.QtWidgets import QLabel, QListWidget, QVBoxLayout, QWidget
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Scenarios"))
        lw = QListWidget()
        lw.addItems(["Checkout Flow", "API Smoke", "Search Load"])
        lay.addWidget(lw)
        lay.addWidget(QLabel("Tasks"))
        tw = QListWidget()
        tw.addItems(["GET /home (w2)", "POST /checkout (w3)", "GET /search (w1)"])
        lay.addWidget(tw)
        return w

    def _make_right_panel(self) -> Any:
        from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout, QWidget
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(QLabel("Live log"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setAccessibleName("Live log")
        lay.addWidget(self.log_text)
        return w

    def _make_build_tab(self) -> Any:
        w = QWidget()
        lay = QVBoxLayout(w)
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

        row = QHBoxLayout()
        self.task_name = QLineEdit("Get Home")
        self.task_name.setAccessibleName("Task name")
        self.task_path = QLineEdit("/")
        self.task_path.setAccessibleName("Task path")
        self.task_method = QComboBox()
        self.task_method.addItems(["GET", "POST"])
        self.task_weight = QSpinBox()
        self.task_weight.setValue(1)
        row.addWidget(self.task_name)
        row.addWidget(self.task_method)
        row.addWidget(self.task_path)
        row.addWidget(QLabel("w"))
        row.addWidget(self.task_weight)
        add_btn = QPushButton("Add task")
        add_btn.setAccessibleName("Add task")
        add_btn.clicked.connect(self._add_task)
        row.addWidget(add_btn)
        lay.addLayout(row)
        return w

    def _add_task(self) -> None:
        t = {
            "name": self.task_name.text(),
            "method": self.task_method.currentText(),
            "path": self.task_path.text(),
            "weight": self.task_weight.value(),
            "kind": "http",
        }
        self._tasks.append(t)
        self.task_list.addItem(f"{t['method']} {t['path']} (w{t['weight']}) - {t['name']}")
        if hasattr(self, "empty_tasks_label"):
            self.empty_tasks_label.hide()

    def _make_run_tab(self) -> Any:
        w = QWidget()
        lay = QVBoxLayout(w)
        cfg = QFormLayout()
        self.users_spin = QSpinBox()
        self.users_spin.setValue(10)
        self.spawn_spin = QDoubleSpinBox()
        self.spawn_spin.setValue(2.0)
        self.runtime_edit = QLineEdit("10s")
        self.csv_edit = QLineEdit("studio")
        cfg.addRow("Users", self.users_spin)
        cfg.addRow("Spawn rate", self.spawn_spin)
        cfg.addRow("Run time", self.runtime_edit)
        cfg.addRow("CSV prefix", self.csv_edit)
        lay.addLayout(cfg)

        self.run_btn = QPushButton("Run")
        self.run_btn.setAccessibleName("Run load test")
        self.run_btn.setToolTip("Start the load test (Ctrl+R)")
        self.run_btn.clicked.connect(self._run)
        lay.addWidget(self.run_btn)

        self.stats_table = QTableWidget(0, 6)
        self.stats_table.setAccessibleName("Endpoint statistics")
        self.stats_table.setHorizontalHeaderLabels(["Name", "Reqs", "Fails", "Avg", "p95", "RPS"])
        lay.addWidget(self.stats_table)

        try:
            import pyqtgraph as pg
            self.chart = pg.PlotWidget()
            self.chart.setBackground(None)
            self.chart.setTitle("RPS over time")
            self.chart.showGrid(x=True, y=True, alpha=0.2)
            self.chart.setMinimumHeight(180)
        except ImportError:
            self.chart = QLabel("Install pyqtgraph for live charts")
        lay.addWidget(self.chart)

        self.status_label = QLabel("Ready to run")
        lay.addWidget(self.status_label)
        return w

    def _run(self) -> None:
        if not self._tasks:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No tasks", "Add at least one task before running.")
            return
        kwargs = {
            "host": self.host_edit.text(),
            "wait_min": self.wait_min_edit.text(),
            "wait_max": self.wait_max_edit.text(),
            "tasks": list(self._tasks),
            "users": self.users_spin.value(),
            "spawn_rate": self.spawn_spin.value(),
            "run_time": self.runtime_edit.text(),
            "csv_prefix": self.csv_edit.text(),
        }
        self.run_btn.setEnabled(False)
        self.status_label.setText("Running load test...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate
        self._worker = RunWorker(kwargs)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_finished(self, stats: dict[str, Any]) -> None:
        self.run_btn.setEnabled(True)
        self.status_label.setText("Run complete")
        self.progress_bar.setVisible(False)
        self.stats_table.setRowCount(0)
        for r in stats.get("rows", []):
            row = self.stats_table.rowCount()
            self.stats_table.insertRow(row)
            self.stats_table.setItem(row, 0, QTableWidgetItem(str(r.get("name"))))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(r.get("request_count"))))
            self.stats_table.setItem(row, 2, QTableWidgetItem(str(r.get("failure_count"))))
            self.stats_table.setItem(row, 3, QTableWidgetItem(str(round(r.get("average", 0), 1))))
            self.stats_table.setItem(row, 4, QTableWidgetItem(str(r.get("p95"))))
            self.stats_table.setItem(row, 5, QTableWidgetItem(str(round(r.get("rps", 0), 1))))
        # store for report tab
        self._last_stats = stats
        self.report_text.setText(str(stats))
        if hasattr(self, "log_text"):
            self.log_text.append(f"Run finished: {stats.get('aggregated', {})}")

        # update chart if available
        try:
            import pyqtgraph as pg
            if isinstance(self.chart, pg.PlotWidget):
                rps_vals = [r.get("rps", 0) for r in stats.get("rows", [])]
                self.chart.clear()
                if rps_vals:
                    self.chart.plot(list(range(len(rps_vals))), rps_vals, pen="c")
        except ImportError:
            return

    def _on_error(self, msg: str) -> None:
        self.run_btn.setEnabled(True)
        self.status_label.setText("Run failed")
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Error", msg)

    def _make_report_tab(self) -> Any:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.report_text = QLabel("No run yet.")
        self.report_text.setWordWrap(True)
        self.report_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        lay.addWidget(self.report_text)
        return w

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
