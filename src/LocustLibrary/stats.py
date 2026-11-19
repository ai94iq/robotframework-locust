"""Stats parsing for LocustLibrary."""

import csv
from pathlib import Path

from .scenario import Stats, StatsRow


def parse_stats_csv(path: str | Path) -> Stats:
    """Parse a Locust stats CSV file into a Stats object."""
    stats = Stats()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("Name", "").strip()
            task_type = (row.get("Type") or "").strip()
            if name == "Aggregated":
                name = "Aggregated"
            sr = StatsRow(
                name=name if name else task_type,
                request_count=int(float(row.get("Request Count", 0) or 0)),
                failure_count=int(float(row.get("Failure Count", 0) or 0)),
                median=float(row.get("Median Response Time", 0) or 0),
                average=float(row.get("Average Response Time", 0) or 0),
                min=float(row.get("Min Response Time", 0) or 0),
                max=float(row.get("Max Response Time", 0) or 0),
                rps=float(row.get("Requests/s", 0) or 0),
                failures_s=float(row.get("Failures/s", 0) or 0),
                p50=float(row.get("50%", 0) or 0),
                p90=float(row.get("90%", 0) or 0),
                p95=float(row.get("95%", 0) or 0),
                p99=float(row.get("99%", 0) or 0),
                p999=float(row.get("99.9%", 0) or 0),
            )
            if name == "Aggregated":
                stats.aggregated = sr
            else:
                stats.rows.append(sr)
    if stats.aggregated and stats.aggregated.request_count:
        stats.fail_ratio = stats.aggregated.failure_count / stats.aggregated.request_count
    return stats
