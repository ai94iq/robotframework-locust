"""Locust-style stats table and charts for Studio."""

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from LocustLibrary.reporting import HEADINGS

from .live import Series

# Row keys in the order of Locust's statistics columns.
_KEYS = ("name", "request_count", "failure_count", "median", "p95", "p99", "average", "min", "max",
         "rps", "failures_s")
# A failure count above zero is the only red in the table.
_FAIL_KEYS = ("failure_count", "failures_s")
# Theme colour token for each chart line.
_LINE_TOKENS = {"rps": "pass", "fails": "fail", "p50": "accent", "p95": "second", "users": "focus"}
_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter


def stats_table() -> QTableWidget:
    table = QTableWidget(0, len(HEADINGS))
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAccessibleName("Endpoint statistics")
    for c, heading in enumerate(HEADINGS):
        header = QTableWidgetItem(heading)
        header.setTextAlignment(_RIGHT if c else _LEFT)
        table.setHorizontalHeaderItem(c, header)
    return table


def set_table_colors(table: QTableWidget, colors: dict[str, str]) -> None:
    """Keep the theme's fail and raised tones on the table for the next fill."""
    table.setProperty("failColor", colors["fail"])
    table.setProperty("raisedColor", colors["raised"])


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
    last = len(rows) - 1 if final.get("aggregated") else -1
    for r, row in enumerate(rows):
        for c, key in enumerate(_KEYS):
            item = _item(table, key, row.get(key, 0))
            if r == last:
                _mark_aggregated(table, item)
            table.setItem(r, c, item)
    table.resizeColumnsToContents()


def _item(table: QTableWidget, key: str, value: Any) -> QTableWidgetItem:
    item = QTableWidgetItem(_cell(key, value))
    if key == "name":
        item.setFont(QFont("Inter", 9))
        item.setTextAlignment(_LEFT)
        return item
    item.setTextAlignment(_RIGHT)
    if key in _FAIL_KEYS and (value or 0) > 0:
        item.setForeground(QBrush(QColor(table.property("failColor") or "#f2555a")))
    return item


def _mark_aggregated(table: QTableWidget, item: QTableWidgetItem) -> None:
    font = item.font()
    font.setBold(True)
    item.setFont(font)
    item.setBackground(QBrush(QColor(table.property("raisedColor") or "#232328")))


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
        self._pg = pg
        self._lines = {}
        self._plots: list[Any] = []
        for title, lines in (
            ("Total Requests per Second", (("rps", "RPS"), ("fails", "Failures/s"))),
            ("Response Times (ms)", (("p50", "50th percentile"), ("p95", "95th percentile"))),
            ("Number of Users", (("users", "Users"),)),
        ):
            plot = pg.PlotWidget(title=title)
            plot.showGrid(x=True, y=True, alpha=0.15)
            plot.addLegend(offset=(10, 10))
            plot.setLabel("bottom", "seconds")
            plot.setMinimumHeight(140)
            for key, name in lines:
                self._lines[key] = plot.plot([], [], name=name)
            self._plots.append(plot)
            lay.addWidget(plot)

    def set_colors(self, colors: dict[str, str]) -> None:
        """Paint the plots in the theme: panel ground, muted axes, one token per line."""
        for key, line in self._lines.items():
            line.setPen(self._pg.mkPen(colors[_LINE_TOKENS[key]], width=2))
        for plot in self._plots:
            plot.setBackground(colors["panel"])
            plot.setTitle(plot.plotItem.titleLabel.text, color=colors["ink"], size="10pt")
            for side in ("left", "bottom"):
                axis = plot.getAxis(side)
                axis.setPen(colors["line"])
                axis.setTextPen(colors["muted"])
            plot.plotItem.legend.setLabelTextColor(colors["muted"])

    def draw(self, series: Series) -> None:
        for key, line in self._lines.items():
            line.setData(series.seconds, getattr(series, key))
