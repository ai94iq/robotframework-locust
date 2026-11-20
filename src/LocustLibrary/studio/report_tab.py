"""Report tab: the final Locust stats and links to the Robot log and the Locust report."""

from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .panels import fill_stats, stats_table


class ReportTab(QWidget):  # type: ignore[misc]
    def __init__(self) -> None:
        super().__init__()
        self._log = Path()
        self._reports: list[Path] = []
        lay = QVBoxLayout(self)
        self.summary = QLabel("No run yet.")
        lay.addWidget(self.summary)
        self.table = stats_table()
        lay.addWidget(self.table, 1)
        buttons = QHBoxLayout()
        self.open_log_btn = QPushButton("Open Robot log")
        self.open_log_btn.clicked.connect(lambda: _open(self._log))
        self.open_report_btn = QPushButton("Open Locust report")
        self.open_report_btn.clicked.connect(lambda: _open(self._reports[0]))
        for button in (self.open_log_btn, self.open_report_btn):
            button.setEnabled(False)
            buttons.addWidget(button)
        lay.addLayout(buttons)

    def show_final(self, final: dict[str, Any]) -> None:
        fill_stats(self.table, final)
        aggregated = final.get("aggregated") or {}
        self.summary.setText(
            f"{aggregated.get('request_count', 0)} requests, "
            f"{aggregated.get('failure_count', 0)} failed ({final.get('fail_ratio', 0):.1%})")

    def set_outputs(self, log: Path, reports: list[Path]) -> None:
        self._log, self._reports = log, reports
        self.open_log_btn.setEnabled(log.is_file())
        self.open_report_btn.setEnabled(bool(reports))


def _open(path: Path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
