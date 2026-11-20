"""Reporting: CSV and HTML export."""

import csv
import html
from collections.abc import Callable
from pathlib import Path
from typing import Any

from locust.html import get_html_report
from locust.stats import StatsCSV

from .scenario import Stats, StatsRow

# Columns and colours of Locust's own web UI statistics table.
_HEADINGS = ("Name", "# Requests", "# Fails", "Median (ms)", "95%ile (ms)", "99%ile (ms)",
             "Average (ms)", "Min (ms)", "Max (ms)", "Current RPS", "Failures/s")
_TABLE = "border-collapse:collapse;background:#121212;color:#f5f5f5;font-family:Roboto,Arial,sans-serif"
_HEAD = "padding:6px 12px;border-bottom:2px solid #54ea92;color:#54ea92;text-align:left"
_CELL = "padding:6px 12px;border-bottom:1px solid #616161"
_FAIL = "color:#f64e56"


def _write_table(path: Path, write_rows: Callable[[Any], None]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        write_rows(csv.writer(handle))


def write_csv_report(
    env: Any,
    base_filepath: str,
    full_history: bool = True,
    output_dir: str | None = None,
) -> str:
    """Write one snapshot of Locust CSV stats. Returns the base path."""
    from .validation import validate_output_path

    base = validate_output_path(base_filepath, output_dir)
    table = StatsCSV(env, [0.5, 0.9, 0.95, 0.99, 0.999])
    _write_table(Path(base + "_stats.csv"), table.requests_csv)
    _write_table(Path(base + "_failures.csv"), table.failures_csv)
    _write_table(Path(base + "_exceptions.csv"), table.exceptions_csv)
    # The streaming history writer never returns, so a one-shot export
    # records only the header.
    if full_history:
        Path(base + "_stats_history.csv").write_text("Timestamp\n", encoding="utf-8")
    return base


def write_html_report(env: Any) -> str:
    """Generate the Locust HTML report."""
    report = get_html_report(env)  # type: ignore[no-untyped-call]
    return str(report)


def stats_table_html(stats: Stats) -> str:
    """One row per request name, then the aggregated row, for the Robot log."""
    head = "".join(f'<th style="{_HEAD}">{name}</th>' for name in _HEADINGS)
    body = "".join(_table_row(r, total=False) for r in stats.rows)
    if stats.aggregated:
        body += _table_row(stats.aggregated, total=True)
    return f'<table style="{_TABLE}"><tr>{head}</tr>{body}</table>'


def _table_row(row: StatsRow, total: bool) -> str:
    cells = [html.escape(row.name), row.request_count, row.failure_count, f"{row.median:.0f}",
             f"{row.p95:.0f}", f"{row.p99:.0f}", f"{row.average:.0f}", f"{row.min:.0f}",
             f"{row.max:.0f}", f"{row.rps:.2f}", f"{row.failures_s:.2f}"]
    styles = [_CELL] * len(cells)
    if row.failure_count:
        styles[2] = f"{_CELL};{_FAIL}"
    weight = ' style="font-weight:bold"' if total else ""
    tds = "".join(f'<td style="{style}">{cell}</td>' for style, cell in zip(styles, cells, strict=True))
    return f"<tr{weight}>{tds}</tr>"


# Spreadsheets run a cell that starts with one of these as a formula.
_FORMULA_START = ("=", "+", "-", "@", "\t", "\r")


def _cell(value: object) -> object:
    if isinstance(value, str) and value.startswith(_FORMULA_START):
        return "'" + value
    return value


def write_stats_csv(
    stats: Stats, base_filepath: str, output_dir: str | None = None
) -> str:
    """Write saved stats to CSV. Returns the validated base path."""
    from .validation import validate_output_path

    base = validate_output_path(base_filepath, output_dir)
    path = Path(f"{base}_stats.csv")
    fields = (
        "name", "request_count", "failure_count",
        "p50", "p90", "p95", "p99", "p999",
    )
    rows = list(stats.rows)
    if stats.aggregated is not None:
        rows.append(stats.aggregated)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: _cell(getattr(row, name)) for name in fields})
    return base
