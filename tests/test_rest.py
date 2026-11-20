"""Remaining branches in the library."""

import subprocess
from pathlib import Path

import pytest

from LocustLibrary import LocustLibrary
from LocustLibrary.runner import _parse_time, _patch_gevent
from LocustLibrary.scenario import Stats, StatsRow
from LocustLibrary.validation import sanitize_prefix, validate_output_path
from LocustLibrary.webui import stop_web_ui


def test_wait_units_and_missing_scenario() -> None:
    lib = LocustLibrary()
    for call in (
        lambda: lib.set_wait_time("1s", "2s"),
        lambda: lib.add_get_request("home", "/"),
        lambda: lib.add_post_request("post", "/"),
        lambda: lib.add_task("login", "Login"),
        lambda: lib.set_on_start("Open"),
        lambda: lib.set_on_stop("Close"),
    ):
        with pytest.raises(RuntimeError, match="Create Load Test"):
            call()
    lib.create_load_test("http://127.0.0.1")
    lib.add_get_request("home", "/")
    lib.add_post_request("save", "/save")
    lib.add_task("login", "Login")
    lib.set_wait_time("10ms", "1m")
    assert lib._scenario is not None
    assert lib._scenario.wait_min == pytest.approx(0.01)
    assert lib._scenario.wait_max == pytest.approx(60)
    lib.set_wait_time("2s", "1h")
    assert lib._scenario.wait_min == pytest.approx(2)
    assert lib._scenario.wait_max == pytest.approx(3600)
    lib.set_wait_time("3", "4")
    assert lib._scenario.wait_min == pytest.approx(3)


def test_checks_pass_and_fail(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    lib = LocustLibrary()
    row = StatsRow(
        name="/", request_count=10, failure_count=1, p50=20.0, rps=5.0, average=1.0
    )
    agg = StatsRow(
        name="Aggregated", request_count=10, failure_count=1, p50=20.0, rps=5.0
    )
    lib._stats = Stats(rows=[row], aggregated=agg, fail_ratio=0.1)
    assert lib.get_locust_stats()["fail_ratio"] == 0.1
    assert lib.get_aggregated_stats()["rps"] == 5.0
    lib.should_meet_response_time("/", "p50", "1s")
    with pytest.raises(AssertionError):
        lib.should_meet_response_time("/", "p50", "1ms")
    with pytest.raises(AssertionError):
        lib.should_have_no_failures()
    with pytest.raises(AssertionError):
        lib.should_meet_throughput("9")
    lib.should_meet_throughput("1")
    with pytest.raises(AssertionError):
        lib.should_meet_error_rate("0%")
    agg.failure_count = 0
    lib.should_have_no_failures()
    lib.should_meet_error_rate("1%")
    lib.export_report("out")
    assert (tmp_path / "out_stats.csv").is_file()
    empty = StatsRow(name="/", request_count=0, p50=0.0)
    lib._stats = Stats(rows=[empty], aggregated=empty)
    with pytest.raises(RuntimeError, match="No requests"):
        lib.should_meet_response_time("/", "p50", "1s")
    lib._stats = Stats(rows=[], aggregated=None)
    with pytest.raises(RuntimeError, match="No stats"):
        lib.should_have_no_failures()
    fresh = LocustLibrary()
    with pytest.raises(RuntimeError, match="No stats"):
        fresh.should_meet_response_time("/", "p50", "1s")
    lib._stats = Stats(rows=[row], aggregated=agg)
    lib.should_meet_response_time("total", "p50", "1s")
    with pytest.raises(RuntimeError, match="not found"):
        lib.should_meet_response_time("missing", "p50", "1s")


def test_run_load_test_stores_stats(monkeypatch) -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    stored = Stats()
    monkeypatch.setattr("LocustLibrary.run_load_test", lambda *_args, **_kwargs: stored)
    lib.run_load_test(users=1, spawn_rate=1, run_time="1s")
    assert lib._stats is stored
    assert lib._config is not None


def test_stop_with_nothing_running() -> None:
    lib = LocustLibrary()
    lib.stop_locust_web()
    lib.stop_distributed()

    class Proc:
        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            return None

        def wait(self, timeout: float = 10) -> int:
            return 0

    lib._web_proc = Proc()  # type: ignore[assignment]
    lib.stop_locust_web()
    assert lib._web_proc is None


def test_time_units_and_gevent_patch() -> None:
    assert _parse_time("2m") == 120
    assert _parse_time("1h") == 3600
    assert _parse_time("15") == 15
    _patch_gevent()
    _patch_gevent()


def test_web_stop_kills_when_wait_expires() -> None:
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
    stop_web_ui(proc)  # type: ignore[arg-type]
    assert proc.killed


def test_empty_name_and_escaped_output(tmp_path: Path, monkeypatch) -> None:
    assert sanitize_prefix("///") == "locust"
    monkeypatch.setattr(
        "LocustLibrary.validation.os.path.basename", lambda _name: "\\"
    )
    assert sanitize_prefix("kept") == "locust"
    monkeypatch.undo()
    outside = (tmp_path.parent / "outside-target").resolve()
    real_resolve = Path.resolve

    def resolve(self: Path, *args: object, **kwargs: object) -> Path:
        if self.name == "bad":
            return outside
        return real_resolve(self, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)
    with pytest.raises(ValueError, match="escapes"):
        validate_output_path("bad", str(tmp_path))
