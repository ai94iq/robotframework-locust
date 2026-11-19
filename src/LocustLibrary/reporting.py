"""Reporting: CSV and HTML export."""

import csv
from collections.abc import Callable
from pathlib import Path
from typing import Any

from locust.html import get_html_report
from locust.stats import StatsCSV

from .scenario import Stats


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
            writer.writerow({name: getattr(row, name) for name in fields})
    return base
