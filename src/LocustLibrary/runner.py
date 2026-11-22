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
from .scenario import RunConfig, Scenario, Stats
from .shape import StageShape
from .stats import _stats_from_env
from .stoprules import RuleWatch
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
    calls = _observe(env, config.mask)
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
        watch = RuleWatch(config.stop_rules, runner)
        breaker = fail_breaker(runner, config.stop_on_fail_ratio, config.fail_ratio_warmup)
        tripped: list[str] = []

        def breaker_check(elapsed: float) -> str:
            reason = breaker(elapsed)
            tripped.append(reason)
            return reason

        stopped = _wait_until(seconds, budget, _first_reason(breaker_check, watch.check))
        runner.quit()
        runner.greenlet.join(timeout=10)
    history.kill(block=False)
    stats = _finish(env, calls)
    stats.stopped, stats.stop_failed, stats.stop_machine = _stop_outcome(
        stopped, tripped, watch, config.breaker_fails)
    return stats


def _stop_outcome(stopped: str, tripped: list[str], watch: Any, breaker_fails: bool) -> tuple[str, bool, bool]:
    """Stop text, failed, load-machine stop; a fail-ratio breaker stop is never a load-machine stop."""
    broke = bool(stopped) and stopped == tripped[-1]
    return stopped, watch.failed or (broke and breaker_fails), watch.machine and not broke


def _first_reason(*checks: Callable[[float], str]) -> Callable[[float], str]:
    return lambda elapsed: next((r for check in checks if (r := check(elapsed))), "")


def _start_history(local: Any) -> Any:
    # Locust fills the report charts from this history; only its own CLI starts the recorder.
    group = Group()
    group.spawn(stats_history, local)
    path = os.environ.get(feed.ENV)
    if path:
        group.spawn(feed.follow, local, path)
    return group


def _observe(env: Any, masked: frozenset[str] = frozenset()) -> CallLog:
    calls = CallLog(masked=masked)
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
