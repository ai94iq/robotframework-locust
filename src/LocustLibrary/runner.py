"""Runner: builds Locust Environment and runs headless."""

import os
import time

from locust import HttpUser
from locust.env import Environment

from .scenario import Scenario, RunConfig, Stats, StatsRow, Task


def _make_task_fn(task: Task):
    """Build a module-level task function for a Task."""

    def task_fn(user):
        if task.kind == "http":
            method = task.method.upper()
            fn = getattr(user.client, method.lower(), None)
            if fn is None:
                return
            fn(task.path, headers=task.headers or {}, data=task.body, name=task.name)

    task_fn.__name__ = task.name.replace(" ", "_")
    return task_fn


_PATCHED = {"done": False}


def _patch_gevent() -> None:
    if _PATCHED["done"]:
        return
    if os.environ.get("LOCUST_SKIP_MONKEY_PATCH") != "1":
        os.environ["LOCUST_SKIP_MONKEY_PATCH"] = "1"
    try:
        import gevent.monkey

        if not getattr(gevent.monkey, "_rf_patched", False):
            gevent.monkey.patch_all()
            gevent.monkey._rf_patched = True
    except Exception:
        pass
    _PATCHED["done"] = True


def _stats_from_env(env) -> Stats:
    stats = Stats()
    rs = env.stats
    for (method, name), entry in (rs.entries or {}).items():
        sr = StatsRow(
            name=name if name else "/",
            request_count=getattr(entry, "num_requests", 0),
            failure_count=getattr(entry, "num_failures", 0),
            median=getattr(entry, "median_response_time", 0.0),
            average=getattr(entry, "avg_response_time", 0.0),
            min=getattr(entry, "min_response_time", 0.0),
            max=getattr(entry, "max_response_time", 0.0),
            rps=getattr(entry, "total_rps", 0.0),
            failures_s=0.0,
            p50=entry.get_response_time_percentile(0.5) if hasattr(entry, "get_response_time_percentile") else 0.0,
            p90=entry.get_response_time_percentile(0.9) if hasattr(entry, "get_response_time_percentile") else 0.0,
            p95=entry.get_response_time_percentile(0.95) if hasattr(entry, "get_response_time_percentile") else 0.0,
            p99=entry.get_response_time_percentile(0.99) if hasattr(entry, "get_response_time_percentile") else 0.0,
        )
        stats.rows.append(sr)
    total = rs.total
    agg = StatsRow(
        name="Aggregated",
        request_count=getattr(total, "num_requests", 0),
        failure_count=getattr(total, "num_failures", 0),
        median=getattr(total, "median_response_time", 0.0),
        average=getattr(total, "avg_response_time", 0.0),
        min=getattr(total, "min_response_time", 0.0),
        max=getattr(total, "max_response_time", 0.0),
        rps=getattr(total, "total_rps", 0.0),
        failures_s=0.0,
        p50=total.get_response_time_percentile(0.5) if hasattr(total, "get_response_time_percentile") else 0.0,
        p90=total.get_response_time_percentile(0.9) if hasattr(total, "get_response_time_percentile") else 0.0,
        p95=total.get_response_time_percentile(0.95) if hasattr(total, "get_response_time_percentile") else 0.0,
        p99=total.get_response_time_percentile(0.99) if hasattr(total, "get_response_time_percentile") else 0.0,
    )
    stats.aggregated = agg
    if agg.request_count:
        stats.fail_ratio = agg.failure_count / agg.request_count
    return stats


def run_load_test(scenario: Scenario, config: RunConfig) -> Stats:
    """Run a load test headless and return parsed stats."""
    _patch_gevent()

    task_fns = [_make_task_fn(t) for t in scenario.tasks]
    weighted: list = []
    for t, fn in zip(scenario.tasks, task_fns):
        weighted.extend([fn] * max(1, t.weight))

    user_class = type(
        "RFUser",
        (HttpUser,),
        {"host": scenario.host, "tasks": weighted, "abstract": False},
    )

    env = Environment(user_classes=[user_class])
    runner = env.create_local_runner()

    runner.start(user_count=config.users, spawn_rate=config.spawn_rate)
    time.sleep(_parse_time(config.run_time))
    runner.quit()
    runner.greenlet.join(timeout=10)

    return _stats_from_env(env)


def _parse_time(value: str) -> float:
    value = value.strip().lower()
    if value.endswith("s"):
        return float(value[:-1])
    if value.endswith("m"):
        return float(value[:-1]) * 60
    if value.endswith("h"):
        return float(value[:-1]) * 3600
    if value.endswith("ms"):
        return float(value[:-2]) / 1000.0
    return float(value)
