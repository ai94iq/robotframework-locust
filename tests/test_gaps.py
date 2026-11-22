"""Covers the library paths the audit left untested."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest
from locust.env import Environment

from LocustLibrary import LocustLibrary
from LocustLibrary.calllog import CallLog
from LocustLibrary.distributed import _stop_one
from LocustLibrary.reporting import write_csv_report, write_html_report
from LocustLibrary.runner import (
    _parse_time,
    run_load_test,
)
from LocustLibrary.scenario import RunConfig, Scenario, Stats, Task
from LocustLibrary.stats import _row_from_entry
from LocustLibrary.users import _make_task_fn
from LocustLibrary.validation import sanitize_prefix, validate_locustfile
from LocustLibrary.webui import start_web_ui


def test_rejects_a_public_web_host(tmp_path, monkeypatch) -> None:
    locustfile = tmp_path / "locustfile.py"
    locustfile.write_text("x = 1\n", encoding="utf-8")
    seen: list[list[str]] = []
    monkeypatch.setattr(
        "LocustLibrary.webui.subprocess.Popen", lambda argv: seen.append(argv)
    )
    start_web_ui(str(locustfile))
    assert seen[0][seen[0].index("--web-host") + 1] == "127.0.0.1"
    with pytest.raises(ValueError, match="loopback"):
        start_web_ui(str(locustfile), host="0.0.0.0")


def test_stop_ignores_a_finished_process() -> None:
    class Finished:
        def poll(self) -> int:
            return 0

        def terminate(self) -> None:
            raise AssertionError("finished process was stopped")

    _stop_one(Finished())  # type: ignore[arg-type]


def test_stop_kills_a_stuck_process() -> None:
    class Proc:
        def __init__(self) -> None:
            self.killed = False

        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float = 10) -> int:
            raise subprocess.TimeoutExpired("locust", timeout)

        def kill(self) -> None:
            self.killed = True

    proc = Proc()
    _stop_one(proc)  # type: ignore[arg-type]
    assert proc.killed


def test_prefix_and_missing_locustfile(tmp_path: Path) -> None:
    assert sanitize_prefix("") == "locust"
    assert sanitize_prefix("..") == "locust"
    assert sanitize_prefix("a/b") == "b"
    with pytest.raises(ValueError, match="not found"):
        validate_locustfile(str(tmp_path / "missing.py"))


def test_csv_snapshot_and_html(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    env = Environment()
    env.create_local_runner()
    base = write_csv_report(env, "out", output_dir=str(tmp_path))
    assert Path(base + "_stats.csv").is_file()
    assert Path(base + "_stats_history.csv").is_file()
    html = write_html_report(env)
    assert "html" in html.lower() or "<" in html


def test_http_task_and_short_run(monkeypatch) -> None:
    seen: list[str] = []

    class Response:
        status_code = 200

        def __enter__(self) -> "Response":  # noqa: PYI034
            return self

        def __exit__(self, *_exc: object) -> None:
            return None

        def success(self) -> None:
            seen.append("ok")

    class Client:
        def get(self, path: str, **_kwargs: object) -> Response:
            seen.append(path)
            return Response()

    class User:
        client = Client()

    task = Task(name="home", kind="http", method="GET", path="/home")
    _make_task_fn(task)(User())
    _make_task_fn(Task(name="nope", kind="http", method="NOPE"))(User())
    assert seen == ["/home", "ok"]
    assert _parse_time("5ms") == 0.005
    assert _row_from_entry("/", object()).p50 == 0.0

    class Greenlet:
        def join(self, timeout: float = 0) -> None:
            return None

    class Local:
        greenlet = Greenlet()

        def start(self, user_count: int, spawn_rate: float) -> None:
            return None

        def quit(self) -> None:
            return None

    monkeypatch.setattr("LocustLibrary.runner._patch_gevent", lambda: None)
    monkeypatch.setattr("LocustLibrary.runner._observe", lambda _env, _mask: CallLog())
    monkeypatch.setattr("LocustLibrary.runner._start_history", lambda _r: SimpleNamespace(kill=lambda **_k: None))
    monkeypatch.setattr("LocustLibrary.runner._finish", lambda _env, _calls: Stats())
    monkeypatch.setattr("LocustLibrary.runner.time.sleep", lambda _seconds: None)
    monkeypatch.setattr(
        "LocustLibrary.runner.Environment",
        lambda **_kwargs: type("Env", (), {"create_local_runner": lambda self: Local()})(),
    )
    scenario = Scenario(host="http://127.0.0.1", tasks=[task])
    stats = run_load_test([scenario], RunConfig(run_time="1s", users=1, spawn_rate=1))
    assert isinstance(stats, Stats)


def test_empty_stats_keywords() -> None:
    lib = LocustLibrary()
    assert lib.get_locust_stats() == {}
    assert lib.get_aggregated_stats() == {}
    with pytest.raises(RuntimeError):
        lib.export_report()
    with pytest.raises(RuntimeError):
        lib.run_load_test()
