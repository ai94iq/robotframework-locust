"""Stop rules end a run once a measured value stays past its limit for the whole window."""

from types import SimpleNamespace
from typing import Any

import pytest

from LocustLibrary import LocustLibrary, stoprules
from LocustLibrary.scenario import Stats
from LocustLibrary.stoprules import RuleWatch, parse_rule


class _Total:
    def __init__(self) -> None:
        self.num_requests = self.num_failures = 0
        self.percentile_ms: float | None = None

    def get_current_response_time_percentile(self, _share: float) -> float | None:
        return self.percentile_ms


def _local() -> Any:
    listeners: list[Any] = []
    events = SimpleNamespace(request=SimpleNamespace(add_listener=listeners.append))
    return SimpleNamespace(stats=SimpleNamespace(total=_Total()),
                           environment=SimpleNamespace(events=events), listeners=listeners)


def _respond(local: Any, code: int, times: int = 1) -> None:
    for _ in range(times):
        local.listeners[0](response=SimpleNamespace(status_code=code))


def test_rule_text_is_read_into_parts() -> None:
    rule = parse_rule("p99.9 > 1.5s for 10s, stop as passed")
    assert (rule.metric, rule.limit, rule.window, rule.fail_run) == ("p99.9", 1500, 10, False)
    assert parse_rule("fail>50%").fail_run and parse_rule("fail>50%").window == 0
    assert parse_rule("rc5?? > 20% for 5s").metric == "rc5??"


@pytest.mark.parametrize("text", ["p95 < 1s", "avg-rt > 1s", "fail > 50% stop", "rc5x > 1%", ""])
def test_unknown_rule_text_is_refused(text: str) -> None:
    with pytest.raises(ValueError, match="Stop rule"):
        parse_rule(text)


def test_percentile_rule_fires_only_after_the_window() -> None:
    local = _local()
    watch = RuleWatch([parse_rule("p95 > 1s for 10s")], local)
    local.stats.total.percentile_ms = 2000
    assert watch.check(1) == "" and watch.check(10) == ""
    assert watch.check(11) == "stopped after 11 s: p95 > 1s for 10s"
    assert watch.failed


def test_a_dip_restarts_the_window() -> None:
    local = _local()
    watch = RuleWatch([parse_rule("p95 > 1s for 5s")], local)
    local.stats.total.percentile_ms = 2000
    watch.check(1)
    local.stats.total.percentile_ms = 10
    watch.check(3)
    local.stats.total.percentile_ms = 2000
    assert watch.check(4) == "" and watch.check(8) == "" and watch.check(9) != ""


def test_fail_rule_reads_failures_since_the_last_check() -> None:
    local = _local()
    watch = RuleWatch([parse_rule("fail > 50%, stop as passed")], local)
    local.stats.total.num_requests, local.stats.total.num_failures = 100, 90
    watch.check(1)
    local.stats.total.num_requests, local.stats.total.num_failures = 200, 100
    assert watch.check(2) == ""
    local.stats.total.num_requests, local.stats.total.num_failures = 300, 190
    assert watch.check(3) == "stopped after 3 s: fail > 50%, stop as passed"
    assert not watch.failed


def test_code_rule_counts_matching_responses() -> None:
    local = _local()
    watch = RuleWatch([parse_rule("rc5?? > 20%")], local)
    _respond(local, 200, 9)
    _respond(local, 503)
    assert watch.check(1) == ""
    _respond(local, 200, 1)
    _respond(local, 500, 1)
    assert watch.check(2) != ""


def test_a_tick_without_responses_keeps_the_window() -> None:
    local = _local()
    watch = RuleWatch([parse_rule("rc404 > 50% for 2s")], local)
    _respond(local, 404)
    watch.check(1)
    assert watch.check(2) == ""
    _respond(local, 404)
    assert watch.check(3) != ""


def test_a_quiet_second_never_fires() -> None:
    local = _local()
    watch = RuleWatch([parse_rule("fail > 0%"), parse_rule("rc4* > 0%")], local)
    assert watch.check(1) == ""


def test_load_machine_rules_read_cpu_and_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(cpu_percent=lambda: 95.0, virtual_memory=lambda: SimpleNamespace(percent=40.0))
    monkeypatch.setattr(stoprules, "psutil", fake)
    assert RuleWatch([parse_rule("mem > 90%")], _local()).check(1) == ""
    assert RuleWatch([parse_rule("cpu > 90%")], _local()).check(1) != ""


def test_a_failed_stop_fails_the_keyword(monkeypatch: pytest.MonkeyPatch) -> None:
    import LocustLibrary as lib_module

    seen: list[Any] = []
    monkeypatch.setattr(lib_module, "run_load_test", lambda _s, config: seen.append(config.stop_rules)
                        or Stats(stopped="stopped after 3 s: cpu > 90%", stop_failed=True))
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1", allowed_hosts="127.0.0.1")
    lib.add_stop_rule("cpu > 90% for 5s")
    with pytest.raises(AssertionError, match="cpu > 90%"):
        lib.run_load_test(users=1)
    assert seen[0][0].metric == "cpu"


def test_a_rule_needs_a_load_test_first() -> None:
    with pytest.raises(RuntimeError, match="Create Load Test"):
        LocustLibrary().add_stop_rule("cpu > 90%")


def test_p999_rule_reads_the_99_9th_percentile() -> None:
    local = _local()
    shares: list[float] = []
    local.stats.total.get_current_response_time_percentile = shares.append
    RuleWatch([parse_rule("p999 > 1s"), parse_rule("p99.9 > 1s")], local).check(1)
    assert shares == pytest.approx([0.999, 0.999])
