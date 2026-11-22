"""Run tab: run the open suite under Robot, or the Build tab's tasks in process, with live charts."""

import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
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
from .worker import RunWorker


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
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(10)
        lay.addWidget(self._settings())
        self._buttons()
        self._started = 0.0
        self.stats_table = stats_table()
        self.stats_table.setMaximumHeight(170)
        lay.addWidget(self.stats_table)
        self.charts = Charts()
        lay.addWidget(self.charts, 1)
        # The window's header row shows the status pill and the Run and Stop buttons.
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("pill")
        self.status_label.setAccessibleName("Run status")

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

    def _buttons(self) -> None:
        self.run_btn = QPushButton("Run")
        self.run_btn.setAccessibleName("Run load test")
        self.run_btn.setToolTip("Start the load test (Ctrl+R)")
        self.run_btn.clicked.connect(self.run)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("ghost")
        self.stop_btn.setAccessibleName("Stop the run")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)

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
        self._started = time.monotonic()
        self._set_status("Running 0 s", running=True)
        if self._suite:
            self._suite_run = start_suite(self._suite)
            self.console.emit(f"Output: {self._suite_run.outdir}\n")
            self.stop_btn.setEnabled(True)
        else:
            self._start_built_tasks(scenario)
            self.stop_btn.setEnabled(True)
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
        elif self._worker:
            self._worker.stop()
            self.console.emit("Stopping...\n")

    def _tick(self) -> None:
        self._set_status(f"Running {time.monotonic() - self._started:.0f} s", running=True)
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
            fill_stats(self.stats_table, update.points[-1]["table"])
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
        self._set_status(text, running=False)

    def _set_status(self, text: str, running: bool) -> None:
        self.status_label.setText(text)
        if self.status_label.property("running") != running:
            self.status_label.setProperty("running", running)
            # Qt applies a property-based style only after a re-polish.
            self.status_label.style().unpolish(self.status_label)
            self.status_label.style().polish(self.status_label)

    def _show_final(self, final: dict[str, Any]) -> None:
        fill_stats(self.stats_table, final)
        self.final.emit(final)

    def _on_finished(self, stats: dict[str, Any]) -> None:
        self._tick()
        self._timer.stop()
        stopped = self._worker is not None and self._worker.stopped
        self._set_idle("Run stopped" if stopped else "Run complete")
        self.stop_btn.setEnabled(False)
        self._show_final(stats)

    def _on_error(self, msg: str) -> None:
        self._timer.stop()
        self._set_idle("Run failed")
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Error", msg)
