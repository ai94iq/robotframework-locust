"""Guards from the 2026-11-20 review: zero requests, failure breaker, host allowlist, body text."""

from types import SimpleNamespace
from typing import Any, Self

import pytest

from LocustLibrary import LocustLibrary, runner, users
from LocustLibrary.scenario import Stats, StatsRow, Task
from LocustLibrary.validation import allowed_hosts, validate_host


def _lib(rows: list[StatsRow]) -> LocustLibrary:
    lib = LocustLibrary()
    lib._stats = Stats(rows=rows, aggregated=StatsRow("Aggregated", request_count=sum(r.request_count for r in rows)))
    return lib


def test_response_time_refuses_an_endpoint_with_no_requests() -> None:
    lib = _lib([StatsRow("login", request_count=0), StatsRow("home", request_count=5, p95=10)])
    with pytest.raises(RuntimeError, match="No requests recorded"):
        lib.should_meet_response_time("login", "p95", "1000ms")


def test_response_time_still_judges_an_endpoint_with_requests() -> None:
    lib = _lib([StatsRow("home", request_count=5, p95=10)])
    lib.should_meet_response_time("home", "p95", "1000ms")


class _Total:
    def __init__(self, requests: int, ratio: float) -> None:
        self.num_requests, self.fail_ratio = requests, ratio


def _local(requests: int, ratio: float) -> Any:
    return SimpleNamespace(stats=SimpleNamespace(total=_Total(requests, ratio)))


def test_breaker_waits_for_the_warmup() -> None:
    check = runner.fail_breaker(_local(50, 1.0), limit=0.2, warmup=10)
    assert check(5) == ""


def test_breaker_trips_over_the_limit_after_warmup() -> None:
    check = runner.fail_breaker(_local(50, 0.5), limit=0.2, warmup=10)
    assert check(12) == "stopped after 12 s: failure ratio 50.0% is over 20.0%"


def test_breaker_off_or_under_limit_never_trips() -> None:
    assert runner.fail_breaker(_local(50, 0.9), limit=0, warmup=0)(99) == ""
    assert runner.fail_breaker(_local(50, 0.1), limit=0.2, warmup=0)(99) == ""
    assert runner.fail_breaker(_local(0, 0.0), limit=0.2, warmup=0)(99) == ""


def test_wait_stops_when_the_breaker_trips(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter(range(100))
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runner.time, "sleep", lambda _s: None)
    reason = runner._wait_until(60, users.Budget(0), lambda elapsed: "stop" if elapsed >= 3 else "")
    assert reason == "stop" and next(clock) < 10


def test_breaker_reason_reaches_the_log(monkeypatch: pytest.MonkeyPatch) -> None:
    import LocustLibrary as lib_module

    warned: list[str] = []
    monkeypatch.setattr(lib_module.logger, "warn", warned.append)
    monkeypatch.setattr(lib_module, "run_load_test",
                        lambda _s, config: Stats(stopped=f"stopped at {config.stop_on_fail_ratio}"))
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1", allowed_hosts="127.0.0.1")
    lib.run_load_test(users=1, stop_on_fail_ratio="20%", fail_ratio_warmup="15s")
    assert lib._config.stop_on_fail_ratio == 0.2 and lib._config.fail_ratio_warmup == 15
    assert warned[-1] == "Load test stopped at 0.2"


def _breaker_run(monkeypatch: pytest.MonkeyPatch, config: Any) -> Stats:
    from tests.test_shape import _fake_env

    monkeypatch.setattr(runner, "_patch_gevent", lambda: None)
    monkeypatch.setattr(runner, "_observe", lambda _env, _mask: None)
    monkeypatch.setattr(runner, "_start_history", lambda _r: SimpleNamespace(kill=lambda **_k: None))
    monkeypatch.setattr(runner, "_finish", lambda _env, _calls: Stats())
    monkeypatch.setattr(runner, "Environment", _fake_env([]))
    monkeypatch.setattr(runner, "fail_breaker", lambda *_a: lambda _e: "stopped: failure ratio")
    return runner.run_load_test([], config)


def test_breaker_stop_fails_the_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from LocustLibrary.scenario import RunConfig

    stats = _breaker_run(monkeypatch, RunConfig(run_time="5s"))
    assert stats.stopped == "stopped: failure ratio" and stats.stop_failed


def test_breaker_stop_passes_when_breaker_fails_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    from LocustLibrary.scenario import RunConfig

    stats = _breaker_run(monkeypatch, RunConfig(run_time="5s", breaker_fails=False))
    assert stats.stopped and not stats.stop_failed


def test_breaker_fails_reaches_the_config(monkeypatch: pytest.MonkeyPatch) -> None:
    import LocustLibrary as lib_module

    monkeypatch.setattr(lib_module, "run_load_test", lambda _s, _config: Stats())
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1", allowed_hosts="127.0.0.1")
    lib.run_load_test(users=1, breaker_fails=False)
    assert lib._config.breaker_fails is False


def test_host_must_be_on_the_allowlist() -> None:
    assert validate_host("https://iam.dev.example.iq/x", ["iam.dev.example.iq"]) == "https://iam.dev.example.iq/x"
    with pytest.raises(ValueError, match="not in the allowed hosts"):
        validate_host("https://iam.prod.example.iq", ["iam.dev.example.iq"])


def test_allowlist_comes_from_argument_or_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOCUSTLIBRARY_ALLOWED_HOSTS", "a.test, B.test")
    assert allowed_hosts("") == ["a.test", "b.test"]
    assert allowed_hosts("c.test") == ["c.test"]
    monkeypatch.delenv("LOCUSTLIBRARY_ALLOWED_HOSTS")
    assert allowed_hosts("") == []


def test_no_allowlist_warns_once(monkeypatch: pytest.MonkeyPatch) -> None:
    import LocustLibrary as lib_module

    warned: list[str] = []
    monkeypatch.setattr(lib_module.logger, "warn", warned.append)
    monkeypatch.delenv("LOCUSTLIBRARY_ALLOWED_HOSTS", raising=False)
    LocustLibrary().create_load_test("http://127.0.0.1")
    assert warned == ["No allowed hosts set; http://127.0.0.1 is not checked against a list"]


class _Response:
    def __init__(self, text: str) -> None:
        self.status_code, self.text, self.verdict = 200, text, ""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def success(self) -> None:
        self.verdict = "ok"

    def failure(self, message: str) -> None:
        self.verdict = message


@pytest.mark.parametrize(("text", "verdict"), [('{"status":"UP"}', "ok"), ("<html>Error</html>", "expected text 'UP' not in the body")])
def test_body_must_hold_the_expected_text(text: str, verdict: str) -> None:
    response = _Response(text)
    user = SimpleNamespace(client=SimpleNamespace(get=lambda *_a, **_k: response))
    users._run_http(user, Task(name="health", path="/health", expected_text="UP"))
    assert response.verdict == verdict


def test_busy_generator_is_flagged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_stats_from_env", lambda _env: Stats())
    monkeypatch.setattr(runner, "write_html_report", lambda _env: "")
    monkeypatch.delenv(runner.feed.ENV, raising=False)
    env = SimpleNamespace(runner=SimpleNamespace(cpu_warning_emitted=True))
    assert runner._finish(env, runner.CallLog()).cpu_busy


def test_busy_generator_warns_in_the_log(monkeypatch: pytest.MonkeyPatch) -> None:
    import LocustLibrary as lib_module

    warned: list[str] = []
    monkeypatch.setattr(lib_module.logger, "warn", warned.append)
    monkeypatch.setattr(lib_module, "run_load_test", lambda _s, _c: Stats(cpu_busy=True))
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1", allowed_hosts="127.0.0.1")
    lib.run_load_test(users=1)
    assert warned == ["Load generator CPU went over 90%; response times may be too high"]


def test_busy_generator_fails_when_asked(monkeypatch: pytest.MonkeyPatch) -> None:
    import LocustLibrary as lib_module

    monkeypatch.setattr(lib_module, "run_load_test", lambda _s, _c: Stats(cpu_busy=True))
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1", allowed_hosts="127.0.0.1")
    with pytest.raises(AssertionError, match="Load generator CPU went over 90%"):
        lib.run_load_test(users=1, fail_on_busy_cpu=True)


def test_keyword_passes_the_expected_text() -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1", allowed_hosts="127.0.0.1")
    lib.add_get_request("health", "/health", expected_text="UP")
    lib.add_post_request("save", "/x", expected_text="id")
    assert [t.expected_text for t in lib._scenario.tasks] == ["UP", "id"]


_BUSY = "Load generator CPU went over 90%; these numbers may be skewed by an overloaded load machine"


@pytest.mark.parametrize("busy", [True, False])
def test_should_keywords_warn_after_a_busy_run(monkeypatch: pytest.MonkeyPatch, busy: bool) -> None:
    from LocustLibrary import checks

    warned: list[str] = []
    monkeypatch.setattr(checks.logger, "warn", warned.append)
    lib = _lib([StatsRow("home", request_count=5, p95=10, rps=5.0)])
    assert lib._stats is not None
    lib._stats.aggregated = StatsRow("Aggregated", request_count=5, rps=5.0)
    lib._stats.cpu_busy = busy
    lib.should_have_no_failures()
    lib.should_meet_response_time("home", "p95", "1000ms")
    lib.should_meet_throughput("1")
    lib.should_meet_error_rate("1%")
    assert warned == ([_BUSY] * 4 if busy else [])
