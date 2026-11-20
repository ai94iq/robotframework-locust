"""Runner: builds Locust Environment and runs headless."""

import os
import time
from collections.abc import Callable
from typing import Any

from locust import HttpUser, between
from locust.env import Environment
from locust.exception import StopUser

from .scenario import RunConfig, Scenario, Stats, StatsRow, Task
from .shape import StageShape


def _call_keyword(name: str) -> None:
    from robot.api.types import KeywordName
    from robot.libraries.BuiltIn import BuiltIn

    BuiltIn().run_keyword(KeywordName(name))


def _measure_keyword(user: Any, keyword_name: str) -> None:
    request = user.environment.events.request
    with request.measure("RF", keyword_name):
        _call_keyword(keyword_name)


def _run_http(user: Any, task: Task) -> None:
    fn = getattr(user.client, task.method.lower(), None)
    if fn is None:
        return
    with fn(task.path, headers=task.headers or {}, data=task.body, json=task.json,
            name=task.name, catch_response=True) as response:
        if response.status_code in task.expected:
            response.success()
        else:
            response.failure(f"status {response.status_code} not in {list(task.expected)}")


class Budget:
    """Task runs shared by every user, like k6 shared-iterations. 0 means no limit."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.spent = 0

    @property
    def done(self) -> bool:
        return bool(self.limit) and self.spent >= self.limit

    def spend(self) -> None:
        self.spent += 1


def _make_task_fn(task: Task, budget: Budget | None = None) -> Callable[[Any], None]:
    """Build one Locust task for an HTTP call or an RF keyword."""

    def task_fn(user: Any) -> None:
        if budget is not None and budget.done:
            raise StopUser()
        if task.kind == "rf":
            _measure_keyword(user, task.keyword_name)
        elif task.kind == "http":
            _run_http(user, task)
        elif task.kind == "py" and task.function is not None:
            task.function(user)
        if budget is not None:
            budget.spend()

    task_fn.__name__ = task.name.replace(" ", "_") or "task"
    return task_fn


def _keyword_method(keyword_name: str) -> Callable[[Any], None]:
    def method(user: Any) -> None:
        _measure_keyword(user, keyword_name)

    return method


class _RFHttpUser(HttpUser):
    """HttpUser whose TLS check and proxy come from the scenario."""

    abstract = True
    verify_tls = True
    proxy = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[no-untyped-call]
        self.client.verify = self.verify_tls
        if self.proxy:
            # Locust turns off trust_env, so HTTPS_PROXY is never read on its own.
            self.client.proxies = {"http": self.proxy, "https": self.proxy}


def _user_class(scenario: Scenario, tasks: list[Any]) -> type:
    attrs: dict[str, Any] = {
        "host": scenario.host,
        "tasks": tasks,
        "weight": scenario.weight,
        "fixed_count": scenario.fixed_count,
        "verify_tls": scenario.verify_tls,
        "proxy": scenario.proxy,
        "abstract": False,
        "wait_time": between(scenario.wait_min, scenario.wait_max),
    }
    if scenario.on_start:
        attrs["on_start"] = _keyword_method(scenario.on_start)
    if scenario.on_stop:
        attrs["on_stop"] = _keyword_method(scenario.on_stop)
    return type(scenario.name, (_RFHttpUser,), attrs)


_PATCHED = {"done": False}


def _patch_gevent() -> None:
    if _PATCHED["done"]:
        return
    os.environ["LOCUST_SKIP_MONKEY_PATCH"] = "1"
    import gevent.monkey

    if not getattr(gevent.monkey, "_rf_patched", False):
        gevent.monkey.patch_all()
        setattr(gevent.monkey, "_rf_patched", True)  # noqa: B010
    _PATCHED["done"] = True


def _pct(entry: object, quantile: float) -> float:
    reader = getattr(entry, "get_response_time_percentile", None)
    if reader is None:
        return 0.0
    return float(reader(quantile))


def _row_from_entry(name: str, entry: object) -> StatsRow:
    return StatsRow(
        name=name,
        request_count=int(getattr(entry, "num_requests", 0)),
        failure_count=int(getattr(entry, "num_failures", 0)),
        median=float(getattr(entry, "median_response_time", 0.0)),
        average=float(getattr(entry, "avg_response_time", 0.0)),
        min=float(getattr(entry, "min_response_time", 0.0)),
        max=float(getattr(entry, "max_response_time", 0.0)),
        rps=float(getattr(entry, "total_rps", 0.0)),
        failures_s=0.0,
        p50=_pct(entry, 0.5),
        p90=_pct(entry, 0.9),
        p95=_pct(entry, 0.95),
        p99=_pct(entry, 0.99),
        p999=_pct(entry, 0.999),
    )


def _stats_from_env(env: Any) -> Stats:
    stats = Stats()
    rs = env.stats
    for (name, _method), entry in (rs.entries or {}).items():
        stats.rows.append(_row_from_entry(name if name else "/", entry))
    stats.aggregated = _row_from_entry("Aggregated", rs.total)
    if stats.aggregated.request_count:
        counted = stats.aggregated
        stats.fail_ratio = counted.failure_count / counted.request_count
    return stats


def _build_class(scenario: Scenario, budget: Budget) -> type:
    weighted: list[Any] = []
    for task in scenario.tasks:
        weighted.extend([_make_task_fn(task, budget)] * max(1, task.weight))
    return _user_class(scenario, weighted)


def _wait_until(seconds: float, budget: Budget) -> None:
    if not budget.limit:
        time.sleep(seconds)
        return
    end = time.monotonic() + seconds
    while time.monotonic() < end and not budget.done:
        time.sleep(0.5)


def run_load_test(scenarios: list[Scenario], config: RunConfig) -> Stats:
    """Run a load test headless and return parsed stats."""
    _patch_gevent()
    budget = Budget(config.iterations)
    shape = StageShape(config.stages) if config.stages else None
    env = Environment(user_classes=[_build_class(s, budget) for s in scenarios],
                      shape_class=shape)
    runner = env.create_local_runner()
    if shape is None:
        runner.start(user_count=config.users, spawn_rate=config.spawn_rate)
        seconds = _parse_time(config.run_time)
    else:
        runner.start_shape()
        seconds = shape.total
    _wait_until(seconds, budget)
    runner.quit()
    runner.greenlet.join(timeout=10)

    return _stats_from_env(env)


def _parse_time(value: str) -> float:
    value = value.strip().lower()
    if value.endswith("ms"):
        return float(value[:-2]) / 1000.0
    if value.endswith("s"):
        return float(value[:-1])
    if value.endswith("m"):
        return float(value[:-1]) * 60
    if value.endswith("h"):
        return float(value[:-1]) * 3600
    return float(value)
