"""TLS, proxy and per-endpoint error rate, for k6 scripts that set them."""

import pytest
from locust.env import Environment

from LocustLibrary import LocustLibrary, users
from LocustLibrary.scenario import Scenario, Stats, StatsRow


def test_user_skips_tls_and_uses_proxy() -> None:
    scenario = Scenario(host="https://h", verify_tls=False, proxy="http://127.0.0.1:18081")
    user = users._user_class(scenario, [])(Environment())
    assert user.client.verify is False
    assert user.client.proxies == {"http": "http://127.0.0.1:18081",
                                   "https": "http://127.0.0.1:18081"}


def test_user_verifies_tls_by_default() -> None:
    user = users._user_class(Scenario(host="https://h"), [])(Environment())
    assert user.client.verify is True
    assert user.client.proxies == {}


def test_keyword_carries_tls_and_proxy_to_every_class() -> None:
    lib = LocustLibrary()
    lib.create_load_test("https://h", verify_tls=False, proxy="http://127.0.0.1:1")
    lib.add_user_class("token")
    lib.add_user_class("signup")
    assert [(s.verify_tls, s.proxy) for s in lib._scenarios] == [(False, "http://127.0.0.1:1")] * 2


def _lib_with(rows: list[StatsRow]) -> LocustLibrary:
    lib = LocustLibrary()
    agg = StatsRow(name="Aggregated", request_count=200, failure_count=2)
    lib._stats = Stats(rows=rows, aggregated=agg)
    return lib


def test_error_rate_per_endpoint() -> None:
    lib = _lib_with([StatsRow(name="token", request_count=100, failure_count=2),
                     StatsRow(name="register", request_count=100, failure_count=0)])
    lib.should_meet_error_rate("1%", endpoint="register")
    lib.should_meet_error_rate("1%")
    with pytest.raises(AssertionError, match="token"):
        lib.should_meet_error_rate("1%", endpoint="token")


def test_error_rate_unknown_or_empty_endpoint() -> None:
    lib = _lib_with([StatsRow(name="token")])
    with pytest.raises(RuntimeError, match="not found"):
        lib.should_meet_error_rate("1%", endpoint="nope")
    with pytest.raises(RuntimeError, match="No requests"):
        lib.should_meet_error_rate("1%", endpoint="token")
