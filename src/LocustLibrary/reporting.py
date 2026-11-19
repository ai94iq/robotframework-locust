"""Reporting: RF log + CSV/HTML export."""

import os
from pathlib import Path

from locust.stats import StatsCSVFileWriter
from locust import __version__ as locust_version


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


def write_html_report(env) -> str:
    """Generate HTML report string."""
    try:
        from locust import stats as ls

        return ls.get_html_report(env=env)
    except Exception:
        return ""
