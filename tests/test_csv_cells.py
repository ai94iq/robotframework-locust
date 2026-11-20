"""Request names in the stats CSV must not run as spreadsheet formulas."""

import csv
from pathlib import Path

from LocustLibrary.reporting import write_stats_csv
from LocustLibrary.scenario import Stats, StatsRow


def test_formula_names_are_quoted(tmp_path: Path) -> None:
    names = ["=1+1", "+cmd", "-2", "@SUM(A1)", "\tx", "/plain"]
    stats = Stats(rows=[StatsRow(n, request_count=1) for n in names])
    base = write_stats_csv(stats, "out", str(tmp_path))
    with open(f"{base}_stats.csv", newline="", encoding="utf-8") as handle:
        written = [row["name"] for row in csv.DictReader(handle)]
    assert written == ["'=1+1", "'+cmd", "'-2", "'@SUM(A1)", "'\tx", "/plain"]
