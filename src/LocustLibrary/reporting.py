"""Reporting: RF log + CSV/HTML export."""

import csv
from pathlib import Path

from locust.stats import StatsCSVFileWriter

from .scenario import Stats


def write_csv_report(env, base_filepath: str, full_history: bool = True, output_dir: str | None = None) -> str:
    """Write Locust CSV reports. Returns base path."""
    from .validation import validate_output_path

    base_filepath = validate_output_path(base_filepath, output_dir)
    writer = StatsCSVFileWriter(
        environment=env,
        percentiles_to_report=[0.5, 0.9, 0.95, 0.99, 0.999],
        base_filepath=base_filepath,
        full_history=full_history,
    )
    # flush once
    try:
        writer.stats_to_csv()
        writer.stats_to_csv(full_history=True)
    except Exception:
        pass
    try:
        writer.close()
    except Exception:
        pass
    return base_filepath


def write_stats_csv(stats: Stats, base_filepath: str, output_dir: str | None = None) -> str:
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


def write_html_report(env) -> str:
    """Generate HTML report string."""
    try:
        from locust import stats as ls

        return ls.get_html_report(env=env)
    except Exception:
        return ""
