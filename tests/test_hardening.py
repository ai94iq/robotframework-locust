"""Checks the audit left open on the library keywords."""

import pytest

from LocustLibrary import LocustLibrary
from LocustLibrary.runner import _stats_from_env
from LocustLibrary.scenario import Stats, StatsRow
from LocustLibrary.validation import validate_host


def _row(name: str = "/", count: int = 1) -> StatsRow:
    return StatsRow(
        name=name, request_count=count, failure_count=0, p50=10.0, rps=1.0
    )


def test_unknown_percentile_fails() -> None:
    lib = LocustLibrary()
    lib._stats = Stats(rows=[_row()], aggregated=_row("Aggregated"))
    lib.should_meet_response_time("/", "p50", "50ms")
    with pytest.raises(RuntimeError, match="not measured"):
        lib.should_meet_response_time("/", "p75", "50ms")


def test_new_scenario_clears_stats() -> None:
    lib = LocustLibrary()
    lib._stats = Stats(aggregated=_row("Aggregated"))
    lib.create_load_test("http://127.0.0.1:8765")
    assert lib._stats is None


def test_no_requests_fail_the_checks() -> None:
    lib = LocustLibrary()
    lib._stats = Stats(aggregated=_row("Aggregated", count=0))
    with pytest.raises(RuntimeError, match="No requests"):
        lib.should_have_no_failures()
    with pytest.raises(RuntimeError, match="No requests"):
        lib.should_meet_error_rate("1%")


def test_host_needs_a_network_location() -> None:
    assert validate_host("http://127.0.0.1:8765") == "http://127.0.0.1:8765"
    with pytest.raises(ValueError):
        validate_host("http://")
    with pytest.raises(ValueError):
        validate_host("https://user:secret@example.test")


def test_export_writes_csv(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    lib = LocustLibrary()
    lib._stats = Stats(rows=[_row()], aggregated=_row("Aggregated"))
    lib.export_report("locust")
    written = (tmp_path / "locust_stats.csv").read_text(encoding="utf-8")
    assert "/," in written


class _Proc:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.alive = True

    def poll(self) -> int | None:
        if self.alive:
            return None
        return 0

    def terminate(self) -> None:
        self.calls.append("terminate")
        self.alive = False

    def wait(self, timeout: float = 10) -> int:
        return 0


def test_second_web_ui_stops_the_first(tmp_path, monkeypatch) -> None:
    locustfile = tmp_path / "locustfile.py"
    locustfile.write_text("x = 1\n", encoding="utf-8")
    made: list[_Proc] = []

    def start(path: str, port: int = 8089, host: str = "127.0.0.1") -> _Proc:
        proc = _Proc()
        made.append(proc)
        return proc

    monkeypatch.setattr("LocustLibrary.webui.start_web_ui", start)
    lib = LocustLibrary()
    lib.start_locust_web(str(locustfile))
    lib.start_locust_web(str(locustfile))
    assert made[0].calls == ["terminate"]
    assert lib._web_proc is made[1]


def test_distributed_stop_closes_handles(tmp_path, monkeypatch) -> None:
    locustfile = tmp_path / "locustfile.py"
    locustfile.write_text("x = 1\n", encoding="utf-8")
    made: list[_Proc] = []

    def popen(argv: list[str], **_unused: object) -> _Proc:
        proc = _Proc()
        made.append(proc)
        return proc

    monkeypatch.setattr("LocustLibrary.distributed.subprocess.Popen", popen)
    lib = LocustLibrary()
    lib.run_distributed(str(locustfile), processes=1)
    lib.stop_distributed()
    assert [proc.calls for proc in made] == [["terminate"], ["terminate"]]
    assert lib._dist_master is None


def test_stats_copy_includes_p999() -> None:
    class Entry:
        num_requests = 3
        num_failures = 0
        median_response_time = 1.0
        avg_response_time = 1.0
        min_response_time = 1.0
        max_response_time = 1.0
        total_rps = 1.0

        def get_response_time_percentile(self, quantile: float) -> float:
            if quantile == 0.999:
                return 7.0
            return 1.0

    class Bag:
        def __init__(self) -> None:
            self.entries = {("/", "GET"): Entry()}
            self.total = Entry()

    class Env:
        def __init__(self) -> None:
            self.stats = Bag()

    stats = _stats_from_env(Env())
    assert stats.rows[0].p999 == 7.0
