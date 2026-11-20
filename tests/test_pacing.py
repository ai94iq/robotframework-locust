"""Pacing starts each task run on a fixed interval per user, whatever the response time."""

from types import SimpleNamespace

import locust.user.wait_time as wait_module
import pytest

from LocustLibrary import LocustLibrary
from LocustLibrary.users import Budget, build_class


def _paced_class(interval: str) -> type:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1", allowed_hosts="127.0.0.1")
    lib.add_get_request("home", "/")
    lib.set_pacing(interval)
    assert lib._scenario is not None
    return build_class(lib._scenario, Budget(0))


def test_a_slow_task_waits_only_the_rest_of_the_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    clock = iter([100.0, 100.0, 103.0, 103.0])
    monkeypatch.setattr(wait_module, "perf_counter", lambda: next(clock))
    paced = _paced_class("10s")
    user = SimpleNamespace(_cp_last_run=0.0, _cp_last_wait_time=0.0)
    paced.wait_time(user)
    assert paced.wait_time(user) == pytest.approx(7.0)


def test_pacing_needs_a_load_test_first() -> None:
    with pytest.raises(RuntimeError, match="Create Load Test"):
        LocustLibrary().set_pacing("10s")
