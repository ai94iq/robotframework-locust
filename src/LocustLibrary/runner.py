"""Runner: builds Locust Environment and runs headless."""

import os
import time
import warnings
from collections.abc import Callable
from typing import Any

from gevent.pool import Group
from locust.env import Environment
from locust.stats import stats_history
from urllib3.exceptions import InsecureRequestWarning

from . import feed
from .calllog import CallLog
from .reporting import write_html_report
from .scenario import RunConfig, Scenario, Stats, StatsRow
from .shape import StageShape
from .users import Budget, build_class

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
        failures_s=float(getattr(entry, "total_fail_per_sec", 0.0)),
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


def fail_breaker(local: Any, limit: float, warmup: float) -> Callable[[float], str]:
    """A check that names why the run should stop once failures pass the limit after warm-up."""
    def check(elapsed: float) -> str:
        if not limit or elapsed < warmup:
            return ""
        total = local.stats.total
        if total.num_requests and total.fail_ratio > limit:
            return (f"stopped after {elapsed:.0f} s: failure ratio {total.fail_ratio:.1%} "
                    f"is over {limit:.1%}")
        return ""

    return check


def _wait_until(seconds: float, budget: Budget,
                breaker: Callable[[float], str] | None = None) -> str:
    start = time.monotonic()
    while (now := time.monotonic()) - start < seconds and not budget.done:
        reason = breaker(now - start) if breaker else ""
        if reason:
            return reason
        time.sleep(0.5)
    return ""


def run_load_test(scenarios: list[Scenario], config: RunConfig) -> Stats:
    """Run a load test headless and return parsed stats."""
    _patch_gevent()
    budget = Budget(config.iterations)
    shape = StageShape(config.stages) if config.stages else None
    env = Environment(user_classes=[build_class(s, budget) for s in scenarios],
                      shape_class=shape)
    calls = _observe(env)
    runner = env.create_local_runner()
    history = _start_history(runner)
    # One warning per call drowns the log; the library logs one line per host instead.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", InsecureRequestWarning)
        if shape is None:
            runner.start(user_count=config.users, spawn_rate=config.spawn_rate)
            seconds = _parse_time(config.run_time)
        else:
            runner.start_shape()
            seconds = shape.total
        stopped = _wait_until(seconds, budget, fail_breaker(
            runner, config.stop_on_fail_ratio, config.fail_ratio_warmup))
        runner.quit()
        runner.greenlet.join(timeout=10)
    history.kill(block=False)
    stats = _finish(env, calls)
    stats.stopped = stopped
    return stats


def _start_history(local: Any) -> Any:
    # Locust fills the report charts from this history; only its own CLI starts the recorder.
    group = Group()
    group.spawn(stats_history, local)
    path = os.environ.get(feed.ENV)
    if path:
        group.spawn(feed.follow, local, path)
    return group


def _observe(env: Any) -> CallLog:
    calls = CallLog()
    env.events.request.add_listener(calls.record)
    return calls


def _finish(env: Any, calls: CallLog) -> Stats:
    stats = _stats_from_env(env)
    stats.calls, stats.left_out = calls.entries, calls.left_out
    stats.report_html = write_html_report(env)
    # Locust only prints this to its own log; an overloaded generator inflates response times.
    stats.cpu_busy = bool(getattr(getattr(env, "runner", None), "cpu_warning_emitted", False))
    path = os.environ.get(feed.ENV)
    if path:
        feed.write_final(path, stats)
    return stats


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
