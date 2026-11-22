"""Studio's stats table keeps the theme's colours."""

import os

import pytest

pytest.importorskip("PySide6", reason="PySide6 not installed: Studio panel colours are untested")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from LocustLibrary.studio import panels

ROW = {"name": "home", "request_count": 3, "failure_count": 1, "failures_s": 0.5}
GRAPHITE = {"fail": "#f2555a", "raised": "#232328"}
PAPER = {"fail": "#c0392b", "raised": "#ece9e2"}


def test_theme_switch_repaints_filled_rows() -> None:
    QApplication.instance() or QApplication([])
    table = panels.stats_table()
    panels.set_table_colors(table, GRAPHITE)
    panels.fill_stats(table, {"rows": [ROW], "aggregated": {**ROW, "name": "Aggregated"}})
    panels.set_table_colors(table, PAPER)
    assert table.item(1, 0).background().color().name() == PAPER["raised"]
    assert table.item(0, 2).foreground().color().name() == PAPER["fail"]
    assert table.item(0, 1).foreground().style().name == "NoBrush"
