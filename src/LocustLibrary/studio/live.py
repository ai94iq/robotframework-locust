"""Run a load suite under Robot for Studio and follow its feed and console output."""

import importlib.util
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from LocustLibrary import feed

_ROBOT_PAGES = {"log.html", "report.html"}


def _stdlib_popen() -> Any:
    # Importing Locust swaps in gevent's subprocess, which needs a gevent loop, and on POSIX
    # blanks the module's fork_exec that the original Popen calls. A private copy of the
    # standard module keeps both.
    spec = importlib.util.find_spec("subprocess")
    if spec is None or spec.loader is None:
        raise ImportError("standard subprocess module not found")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Popen


_popen = _stdlib_popen()


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


# Under gevent a POSIX child started with cwd or preexec_fn hangs before exec, so it moves into
# the suite folder itself.
_CHDIR_EXEC = "import os, sys; os.chdir(sys.argv[1]); os.execv(sys.argv[2], sys.argv[2:])"


def _spawn(command: list[str], cwd: str) -> tuple[list[str], dict[str, Any]]:
    # A load run should never slow the desktop it is watched from.
    if sys.platform == "win32":
        return command, {"cwd": cwd, "creationflags": subprocess.BELOW_NORMAL_PRIORITY_CLASS}
    return [sys.executable, "-c", _CHDIR_EXEC, cwd, *command], {}


def _lower_priority(pid: int) -> None:
    if sys.platform != "win32":
        os.setpriority(os.PRIO_PROCESS, pid, os.getpriority(os.PRIO_PROCESS, 0) + 10)


def start_suite(suite: str) -> SuiteRun:
    outdir = Path(tempfile.mkdtemp(prefix="locust-studio-"))
    env = {**os.environ, feed.ENV: str(outdir / "feed.jsonl"), "PYTHONUNBUFFERED": "1"}
    command, options = _spawn(robot_command(suite, outdir), str(Path(suite).parent))
    with (outdir / "console.txt").open("wb") as console:
        process = _popen(command, stdout=console, stderr=subprocess.STDOUT, env=env, shell=False,
                         **options)
    _lower_priority(process.pid)
    return SuiteRun(process, outdir)
