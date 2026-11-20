"""Studio runs a suite under Robot and follows its feed and console."""

import json
import sys
from pathlib import Path
from typing import Any

from LocustLibrary import feed
from LocustLibrary.studio import live


def test_series_counts_seconds_from_the_first_point() -> None:
    series = live.Series()
    series.add({"time": "2026-11-20T12:00:01Z", "rps": 2, "fails": 0, "p50": 4, "p95": 9, "users": 3})
    series.add({"time": "2026-11-20T12:00:04Z", "rps": 5, "fails": 1, "p50": 6, "p95": 8, "users": 3})
    assert series.seconds == [0.0, 3.0]
    assert (series.rps, series.fails, series.p95) == ([2, 5], [0, 1], [9, 8])


def test_command_runs_robot_on_the_suite(tmp_path: Path) -> None:
    cmd = live.robot_command("D:/s/load.robot", tmp_path)
    assert cmd[:3] == [sys.executable, "-m", "robot"]
    assert cmd[-1] == "D:/s/load.robot" and str(tmp_path) in cmd


def test_poll_returns_points_console_and_final(tmp_path: Path) -> None:
    run = live.SuiteRun(process=None, outdir=tmp_path)
    (tmp_path / "console.txt").write_bytes(b"Load    | PASS |\n")
    point = {"time": "t", "rps": 1, "fails": 0, "p50": 1, "p95": 1, "users": 1}
    lines = [json.dumps(point), json.dumps({"final": {"rows": []}})]
    (tmp_path / "feed.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    update = run.poll()
    assert update.points == [point] and update.final == {"rows": []}
    assert update.console == "Load    | PASS |\n"
    assert run.poll().console == ""


def test_reports_found_beside_the_log(tmp_path: Path) -> None:
    for name in ("log.html", "report.html", "iam_load.html"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    run = live.SuiteRun(process=None, outdir=tmp_path)
    assert run.log_file() == tmp_path / "log.html"
    assert run.locust_reports() == [tmp_path / "iam_load.html"]


def test_start_sets_the_feed_and_low_priority(monkeypatch: Any, tmp_path: Path) -> None:
    seen: dict[str, Any] = {}

    def fake_popen(cmd: list[str], **kwargs: Any) -> str:
        seen.update(kwargs, cmd=cmd)
        return "proc"

    monkeypatch.setattr(live, "_popen", fake_popen)
    monkeypatch.setattr(live.tempfile, "mkdtemp", lambda prefix: str(tmp_path))
    run = live.start_suite(str(tmp_path / "load.robot"))
    assert run.process == "proc" and seen["env"][feed.ENV] == str(tmp_path / "feed.jsonl")
    assert seen["cwd"] == str(tmp_path) and seen["shell"] is False
    assert ("creationflags" in seen) == (sys.platform == "win32")
