"""Locust-style stats table and charts for Studio."""

from typing import Any

from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from LocustLibrary.reporting import HEADINGS

from .live import Series

# Row keys in the order of Locust's statistics columns.
_KEYS = ("name", "request_count", "failure_count", "median", "p95", "p99", "average", "min", "max",
         "rps", "failures_s")
# Line colours of Locust's report charts.
_GREEN, _RED, _YELLOW, _PURPLE, _BLUE = "#00ca5a", "#ff6d6d", "#ffca5a", "#9966cc", "#5d8cc2"


def stats_table() -> QTableWidget:
    table = QTableWidget(0, len(HEADINGS))
    table.setHorizontalHeaderLabels(list(HEADINGS))
    table.verticalHeader().setVisible(False)
    table.setAccessibleName("Endpoint statistics")
    return table


def _cell(key: str, value: Any) -> str:
    if key in ("rps", "failures_s"):
        return f"{value or 0:.2f}"
    if isinstance(value, float):
        return str(round(value))
    return str(value)


def fill_stats(table: QTableWidget, final: dict[str, Any]) -> None:
    rows = list(final.get("rows", []))
    if final.get("aggregated"):
        rows.append(final["aggregated"])
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, key in enumerate(_KEYS):
            table.setItem(r, c, QTableWidgetItem(_cell(key, row.get(key, 0))))
    table.resizeColumnsToContents()


class Charts(QWidget):  # type: ignore[misc]
    """The three charts of Locust's report, drawn from the run feed."""

    def __init__(self) -> None:
        super().__init__()
        lay = QVBoxLayout(self)
        try:
            import pyqtgraph as pg
        except ImportError:
            lay.addWidget(QLabel("Install pyqtgraph for live charts"))
            self._lines: dict[str, Any] = {}
            return
        self._lines = {}
        for title, lines in (
            ("Total Requests per Second", (("rps", "RPS", _GREEN), ("fails", "Failures/s", _RED))),
            ("Response Times (ms)", (("p50", "50th percentile", _YELLOW), ("p95", "95th percentile", _PURPLE))),
            ("Number of Users", (("users", "Users", _BLUE),)),
        ):
            plot = pg.PlotWidget(title=title)
            plot.setBackground(None)
            plot.showGrid(x=True, y=True, alpha=0.2)
            plot.addLegend(offset=(10, 10))
            plot.setLabel("bottom", "seconds")
            plot.setMinimumHeight(140)
            for key, name, colour in lines:
                self._lines[key] = plot.plot([], [], pen=pg.mkPen(colour, width=2), name=name)
            lay.addWidget(plot)

    def draw(self, series: Series) -> None:
        for key, line in self._lines.items():
            line.setData(series.seconds, getattr(series, key))
