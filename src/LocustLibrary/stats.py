"""Stats parsing for LocustLibrary."""

import csv
from pathlib import Path
from typing import Any

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


def _pct(entry: object, quantile: float) -> float:
    reader = getattr(entry, "get_response_time_percentile", None)
    if reader is None:
        return 0.0
    return float(reader(quantile))


def _row_from_entry(name: str, entry: object) -> StatsRow:
    return StatsRow(
        name=name,
        request_count=int(getattr(entry, "num_requests", 0)),
        failure_count=int(getattr(entry, "num_failures", 0)),
        median=float(getattr(entry, "median_response_time", 0.0)),
        average=float(getattr(entry, "avg_response_time", 0.0)),
        # Locust keeps no minimum until the first request lands.
        min=float(getattr(entry, "min_response_time", 0.0) or 0.0),
        max=float(getattr(entry, "max_response_time", 0.0)),
        rps=float(getattr(entry, "total_rps", 0.0)),
        failures_s=float(getattr(entry, "total_fail_per_sec", 0.0)),
        p50=_pct(entry, 0.5),
        p90=_pct(entry, 0.9),
        p95=_pct(entry, 0.95),
        p99=_pct(entry, 0.99),
        p999=_pct(entry, 0.999),
    )


def _stats_from_env(env: Any) -> Stats:
    stats = Stats()
    rs = env.stats
    for (name, _method), entry in (rs.entries or {}).items():
        stats.rows.append(_row_from_entry(name if name else "/", entry))
    stats.aggregated = _row_from_entry("Aggregated", rs.total)
    if stats.aggregated.request_count:
        counted = stats.aggregated
        stats.fail_ratio = counted.failure_count / counted.request_count
    return stats
