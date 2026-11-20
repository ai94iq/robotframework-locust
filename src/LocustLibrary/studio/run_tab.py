"""Run tab: run the open suite under Robot, or the Build tab's tasks in process, with live charts."""

import os
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from LocustLibrary import feed

from .live import Series, SuiteRun, Update, start_suite
from .panels import Charts, fill_stats, stats_table


class RunWorker(QThread):  # type: ignore[misc]
    """Runs tasks built on the Build tab in process; the feed file carries the live charts."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, scenario_kwargs: dict[str, Any], feed_path: str) -> None:
        super().__init__()
        self.kwargs = scenario_kwargs
        self.feed_path = feed_path

    def run(self) -> None:
        os.environ[feed.ENV] = self.feed_path
        try:
            from LocustLibrary import LocustLibrary

            lib = LocustLibrary()
            lib.create_load_test(self.kwargs["host"])
            lib.set_wait_time(self.kwargs["wait_min"], self.kwargs["wait_max"])
            for t in self.kwargs["tasks"]:
                add = lib.add_get_request if t["method"] == "GET" else lib.add_post_request
                add(t["name"], t["path"], weight=t["weight"])
            lib.run_load_test(users=self.kwargs["users"], spawn_rate=self.kwargs["spawn_rate"],
                              run_time=self.kwargs["run_time"])
            self.finished.emit(lib.get_locust_stats())
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
        finally:
            os.environ.pop(feed.ENV, None)


class RunTab(QWidget):  # type: ignore[misc]
    console = Signal(str)
    final = Signal(object)
    outputs = Signal(object, object)

    def __init__(self, scenario: Callable[[], dict[str, Any]]) -> None:
        super().__init__()
        self._scenario = scenario
        self._suite = ""
        self._suite_run: SuiteRun | None = None
        self._worker: RunWorker | None = None
        self._feed_path = ""
        self._feed_at = 0
        self.series = Series()
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._tick)
        lay = QVBoxLayout(self)
        lay.addWidget(self._settings())
        lay.addLayout(self._buttons())
        self.stats_table = stats_table()
        self.stats_table.setMaximumHeight(170)
        lay.addWidget(self.stats_table)
        self.charts = Charts()
        lay.addWidget(self.charts, 1)
        self.status_label = QLabel("Ready to run")
        lay.addWidget(self.status_label)

    def _settings(self) -> QWidget:
        self.run_settings = QWidget()
        cfg = QFormLayout(self.run_settings)
        self.users_spin = QSpinBox()
        self.users_spin.setValue(10)
        self.spawn_spin = QDoubleSpinBox()
        self.spawn_spin.setValue(2.0)
        self.runtime_edit = QLineEdit("10s")
        cfg.addRow("Users", self.users_spin)
        cfg.addRow("Spawn rate", self.spawn_spin)
        cfg.addRow("Run time", self.runtime_edit)
        return self.run_settings

    def _buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.run_btn = QPushButton("Run")
        self.run_btn.setAccessibleName("Run load test")
        self.run_btn.setToolTip("Start the load test (Ctrl+R)")
        self.run_btn.clicked.connect(self.run)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setAccessibleName("Stop the run")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        row.addWidget(self.run_btn)
        row.addWidget(self.stop_btn)
        return row

    @property
    def running(self) -> bool:
        return bool(self._timer.isActive())

    def set_suite(self, path: str) -> None:
        self._suite = path
        # The suite's own Run Load Test sets users, spawn rate and run time.
        self.run_settings.setVisible(False)
        self.run_btn.setText(f"Run {Path(path).name}")

    def run(self) -> None:
        scenario = self._scenario()
        if not self._suite and not scenario["tasks"]:
            QMessageBox.warning(self, "Nothing to run", "Open a suite or add a task on the Build tab.")
            return
        self.series = Series()
        self.charts.draw(self.series)
        self.stats_table.setRowCount(0)
        self.run_btn.setEnabled(False)
        self.status_label.setText("Running load test...")
        if self._suite:
            self._suite_run = start_suite(self._suite)
            self.console.emit(f"Output: {self._suite_run.outdir}\n")
            self.stop_btn.setEnabled(True)
        else:
            self._start_built_tasks(scenario)
        self._timer.start()

    def _start_built_tasks(self, scenario: dict[str, Any]) -> None:
        kwargs = {**scenario, "users": self.users_spin.value(), "spawn_rate": self.spawn_spin.value(),
                  "run_time": self.runtime_edit.text()}
        self._feed_path = str(Path(tempfile.mkdtemp(prefix="locust-studio-")) / "feed.jsonl")
        self._feed_at = 0
        self._worker = RunWorker(kwargs, self._feed_path)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _stop(self) -> None:
        if self._suite_run:
            self._suite_run.process.terminate()
            self.console.emit("Stopped.\n")

    def _tick(self) -> None:
        run = self._suite_run
        if run is None:
            records, self._feed_at = feed.read_new(self._feed_path, self._feed_at)
            self._apply(Update([r for r in records if "final" not in r], None, ""))
            return
        ended = run.process.poll() is not None
        # Read after the exit check, so the last lines the run wrote are not missed.
        self._apply(run.poll())
        if ended:
            self._end_suite_run(run)

    def _apply(self, update: Update) -> None:
        if update.console:
            self.console.emit(update.console)
        for point in update.points:
            self.series.add(point)
        if update.points:
            self.charts.draw(self.series)
        if update.final:
            self._show_final(update.final)

    def _end_suite_run(self, run: SuiteRun) -> None:
        self._suite_run = None
        self._timer.stop()
        code = run.process.returncode
        self._set_idle("Run complete" if code == 0 else f"Run ended, Robot exit code {code}")
        self.stop_btn.setEnabled(False)
        self.outputs.emit(run.log_file(), run.locust_reports())

    def _set_idle(self, text: str) -> None:
        self.run_btn.setEnabled(True)
        self.status_label.setText(text)

    def _show_final(self, final: dict[str, Any]) -> None:
        fill_stats(self.stats_table, final)
        self.final.emit(final)

    def _on_finished(self, stats: dict[str, Any]) -> None:
        self._tick()
        self._timer.stop()
        self._set_idle("Run complete")
        self._show_final(stats)

    def _on_error(self, msg: str) -> None:
        self._timer.stop()
        self._set_idle("Run failed")
        QMessageBox.critical(self, "Error", msg)
