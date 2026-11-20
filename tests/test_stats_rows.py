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
