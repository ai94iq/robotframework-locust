"""Run a load suite under Robot for Studio and follow its feed and console output."""

import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from gevent import monkey

from LocustLibrary import feed

_ROBOT_PAGES = {"log.html", "report.html"}
# Importing Locust swaps in gevent's subprocess, which needs gevent's thread pool and fails
# outside a gevent loop; Studio starts Robot with the standard one.
_popen = monkey.get_original("subprocess", "Popen")


@dataclass
class Series:
    """Chart data in Locust's report charts: seconds since the first point."""

    seconds: list[float] = field(default_factory=list)
    rps: list[float] = field(default_factory=list)
    fails: list[float] = field(default_factory=list)
    p50: list[float] = field(default_factory=list)
    p95: list[float] = field(default_factory=list)
    users: list[float] = field(default_factory=list)
    _start: datetime | None = None

    def add(self, point: dict[str, Any]) -> None:
        moment = datetime.fromisoformat(point["time"])
        self._start = self._start or moment
        self.seconds.append((moment - self._start).total_seconds())
        for name in ("rps", "fails", "p50", "p95", "users"):
            getattr(self, name).append(point[name])


@dataclass
class Update:
    points: list[dict[str, Any]]
    final: dict[str, Any] | None
    console: str


@dataclass
class SuiteRun:
    process: Any
    outdir: Path
    _feed_at: int = 0
    _console_at: int = 0

    def poll(self) -> Update:
        records, self._feed_at = feed.read_new(str(self.outdir / "feed.jsonl"), self._feed_at)
        finals = [r["final"] for r in records if "final" in r]
        points = [r for r in records if "final" not in r]
        return Update(points, finals[-1] if finals else None, self._read_console())

    def _read_console(self) -> str:
        console = self.outdir / "console.txt"
        if not console.is_file():
            return ""
        with console.open("rb") as handle:
            handle.seek(self._console_at)
            chunk = handle.read()
        self._console_at += len(chunk)
        return chunk.decode("utf-8", errors="replace")

    def log_file(self) -> Path:
        return self.outdir / "log.html"

    def locust_reports(self) -> list[Path]:
        return sorted(p for p in self.outdir.glob("*.html") if p.name not in _ROBOT_PAGES)


def robot_command(suite: str, outdir: Path) -> list[str]:
    return [sys.executable, "-m", "robot", "--outputdir", str(outdir), "--consolecolors", "off",
            "--consolewidth", "100", suite]


def _low_priority() -> dict[str, Any]:
    # A load run should never slow the desktop it is watched from.
    if sys.platform == "win32":
        return {"creationflags": subprocess.BELOW_NORMAL_PRIORITY_CLASS}
    return {"preexec_fn": lambda: os.nice(10)}


def start_suite(suite: str) -> SuiteRun:
    outdir = Path(tempfile.mkdtemp(prefix="locust-studio-"))
    env = {**os.environ, feed.ENV: str(outdir / "feed.jsonl"), "PYTHONUNBUFFERED": "1"}
    with (outdir / "console.txt").open("wb") as console:
        process = _popen(robot_command(suite, outdir), stdout=console,
               stderr=subprocess.STDOUT, env=env, shell=False,
               cwd=str(Path(suite).parent), **_low_priority())
    return SuiteRun(process, outdir)
