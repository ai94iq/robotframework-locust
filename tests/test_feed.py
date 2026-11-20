"""The run feed gives Studio Locust's per-second history and the final stats."""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from LocustLibrary import feed
from LocustLibrary.scenario import Stats, StatsRow


class _Total:
    current_rps = 2.5
    current_fail_per_sec = 0.5

    def get_current_response_time_percentile(self, percent: float) -> int:
        return {0.5: 400, 0.95: 900}[percent]


def _local(state: str = "running") -> SimpleNamespace:
    entries = {("register", "POST"): SimpleNamespace(num_requests=4, num_failures=1)}
    return SimpleNamespace(stats=SimpleNamespace(total=_Total(), entries=entries),
                           user_count=3, state=state)


def test_snapshot_has_the_chart_values() -> None:
    point = feed.snapshot(_local())
    assert {k: point[k] for k in ("rps", "fails", "p50", "p95", "users")} == {
        "rps": 2.5, "fails": 0.5, "p50": 400, "p95": 900, "users": 3}
    assert point["time"].endswith("+00:00")


def test_snapshot_carries_the_stats_table() -> None:
    table = feed.snapshot(_local())["table"]
    assert [(r["name"], r["request_count"], r["failure_count"]) for r in table["rows"]] == [
        ("register", 4, 1)]
    assert table["aggregated"]["name"] == "Aggregated"


def test_final_stats_line(tmp_path: Path) -> None:
    path = tmp_path / "feed.jsonl"
    stats = Stats(rows=[StatsRow(name="register", request_count=2)],
                  aggregated=StatsRow(name="Aggregated", request_count=2),
                  calls=["x"], report_html="<html>")
    feed.write_final(str(path), stats)
    final = json.loads(path.read_text(encoding="utf-8"))["final"]
    assert final["rows"][0]["name"] == "register"
    assert final["aggregated"]["request_count"] == 2
    assert "calls" not in final and "report_html" not in final


def test_read_new_lines_from_an_offset(tmp_path: Path) -> None:
    path = tmp_path / "feed.jsonl"
    path.write_text('{"a": 1}\n{"b": 2}\n{"c"', encoding="utf-8")
    records, offset = feed.read_new(str(path), 0)
    assert records == [{"a": 1}, {"b": 2}]
    path.write_text('{"a": 1}\n{"b": 2}\n{"c": 3}\n', encoding="utf-8")
    assert feed.read_new(str(path), offset) == ([{"c": 3}], path.stat().st_size)


def test_missing_feed_reads_nothing(tmp_path: Path) -> None:
    assert feed.read_new(str(tmp_path / "none.jsonl"), 0) == ([], 0)


def _follow_once(monkeypatch: Any, local: SimpleNamespace, path: Path) -> None:
    def stop(_seconds: float) -> None:
        raise StopIteration

    monkeypatch.setattr(feed.gevent, "sleep", stop)
    with pytest.raises(StopIteration):
        feed.follow(local, str(path))


def test_follow_writes_while_running(monkeypatch: Any, tmp_path: Path) -> None:
    path = tmp_path / "feed.jsonl"
    _follow_once(monkeypatch, _local(), path)
    assert json.loads(path.read_text(encoding="utf-8"))["rps"] == 2.5


def test_follow_skips_a_stopped_runner(monkeypatch: Any, tmp_path: Path) -> None:
    path = tmp_path / "feed.jsonl"
    _follow_once(monkeypatch, _local("stopped"), path)
    assert not path.exists()
