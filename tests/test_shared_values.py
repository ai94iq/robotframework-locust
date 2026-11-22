"""One step hands generated data to another during a run, like rfswarm's TestDataTable."""

import gevent
import pytest

from LocustLibrary import LocustLibrary
from LocustLibrary.scenario import Stats


def test_values_come_out_in_the_order_they_went_in() -> None:
    lib = LocustLibrary()
    lib.put_shared_value("accounts", "a1")
    lib.put_shared_value("accounts", "a2")
    assert [lib.take_shared_value("accounts"), lib.take_shared_value("accounts")] == ["a1", "a2"]


def test_take_waits_for_another_user_to_put() -> None:
    lib = LocustLibrary()
    taker = gevent.spawn(lib.take_shared_value, "orders", "5s")
    gevent.spawn_later(0.05, lib.put_shared_value, "orders", "o1")
    assert taker.get(timeout=5) == "o1"


def test_an_empty_name_fails_after_the_timeout() -> None:
    with pytest.raises(AssertionError, match="No shared value 'users' within 0.1 s"):
        LocustLibrary().take_shared_value("users", "100ms")


def test_a_new_run_starts_with_no_values(monkeypatch: pytest.MonkeyPatch) -> None:
    import LocustLibrary as lib_module

    monkeypatch.setattr(lib_module, "run_load_test", lambda _s, _c: Stats())
    lib = LocustLibrary()
    lib.put_shared_value("ids", "old")
    lib.create_load_test("http://127.0.0.1", allowed_hosts="127.0.0.1")
    lib.run_load_test(users=1)
    with pytest.raises(AssertionError):
        lib.take_shared_value("ids", "10ms")


def test_a_full_name_refuses_more_values() -> None:
    lib = LocustLibrary(shared_limit=2)
    lib.put_shared_value("ids", 1)
    lib.put_shared_value("ids", 2)
    with pytest.raises(AssertionError, match="Shared value 'ids' is full at 2 values"):
        lib.put_shared_value("ids", 3)


def test_the_default_limit_is_10000_and_0_means_no_limit() -> None:
    assert LocustLibrary()._shared_limit == 10000
    lib = LocustLibrary(shared_limit=0)
    for i in range(10001):
        lib.put_shared_value("ids", i)


def test_a_take_timeout_in_a_run_counts_as_a_failed_request() -> None:
    from types import SimpleNamespace

    from locust.event import Events

    from LocustLibrary import users

    seen: list[dict[str, object]] = []
    events = Events()
    events.request.add_listener(lambda **kw: seen.append(kw))
    users._running.user = SimpleNamespace(environment=SimpleNamespace(events=events))
    try:
        with pytest.raises(AssertionError):
            LocustLibrary().take_shared_value("users", "10ms")
    finally:
        users._running.user = None
    assert [(s["request_type"], s["name"]) for s in seen] == [("SHARED", "Take Shared Value users")]
    assert isinstance(seen[0]["exception"], AssertionError)
