"""Stats rows carry the request name Locust recorded, so per-endpoint checks find them."""

import types

from locust.stats import RequestStats

from LocustLibrary.runner import _stats_from_env


def test_rows_are_named_after_the_request() -> None:
    stats = RequestStats()
    stats.log_request("GET", "home", 12, 10)
    stats.log_request("POST", "login", 30, 10)
    rows = _stats_from_env(types.SimpleNamespace(stats=stats)).rows
    assert sorted(r.name for r in rows) == ["home", "login"]


def test_rows_carry_failures_per_second() -> None:
    stats = RequestStats()
    stats.log_request("POST", "login", 30, 10)
    stats.log_error("POST", "login", "500")
    (row,) = _stats_from_env(types.SimpleNamespace(stats=stats)).rows
    assert row.failures_s == stats.get("login", "POST").total_fail_per_sec
    assert row.failures_s > 0


# The live feed reads stats every second, from before the first request lands.
def test_stats_before_any_request() -> None:
    stats = RequestStats()
    stats.get("login", "POST")
    read = _stats_from_env(types.SimpleNamespace(stats=stats))
    total = read.aggregated
    assert total is not None
    assert (read.rows[0].min, total.min, total.request_count) == (0.0, 0.0, 0)
