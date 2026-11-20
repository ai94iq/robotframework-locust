"""Run feed for Studio: Locust's per-second history and the final stats, as JSON lines.

Run Load Test writes it when LOCUSTLIBRARY_FEED names a file; Studio reads it during the run.
"""

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import gevent

from .scenario import Stats

ENV = "LOCUSTLIBRARY_FEED"


def snapshot(local: Any) -> dict[str, Any]:
    """The values of Locust's report charts right now."""
    total = local.stats.total
    return {"time": datetime.now(UTC).isoformat(), "rps": total.current_rps or 0,
            "fails": total.current_fail_per_sec or 0,
            "p50": total.get_current_response_time_percentile(0.5) or 0,
            "p95": total.get_current_response_time_percentile(0.95) or 0,
            "users": local.user_count or 0}


def follow(local: Any, path: str) -> None:
    # Locust's own history samples every few seconds; live charts need one point a second.
    while True:
        if local.state not in ("ready", "stopped"):
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(snapshot(local)) + "\n")
        gevent.sleep(1)


def write_final(path: str, stats: Stats) -> None:
    final = {"rows": [asdict(row) for row in stats.rows],
             "aggregated": asdict(stats.aggregated) if stats.aggregated else None,
             "fail_ratio": stats.fail_ratio}
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"final": final}) + "\n")


def read_new(path: str, offset: int) -> tuple[list[dict[str, Any]], int]:
    """Whole lines written since offset, and the offset after them."""
    file = Path(path)
    if not file.is_file():
        return [], offset
    with file.open("rb") as handle:
        handle.seek(offset)
        chunk = handle.read()
    done = chunk.rfind(b"\n") + 1
    lines = chunk[:done].decode("utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()], offset + done
