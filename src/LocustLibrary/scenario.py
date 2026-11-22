"""Scenario data shapes for LocustLibrary."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .stoprules import StopRule


@dataclass
class Task:
    """A single load-test task."""

    name: str
    kind: str = "http"  # "http" or "rf"
    weight: int = 1
    method: str = "GET"
    path: str = "/"
    headers: dict[str, str] = field(default_factory=dict)
    body: Any = None
    json: Any = None
    expected: tuple[int, ...] = (200,)
    keyword_name: str = ""
    keyword_args: tuple[Any, ...] = field(default_factory=tuple)
    function: Callable[[Any], None] | None = None
    expected_text: str = ""


@dataclass
class Scenario:
    """A load-test scenario."""

    host: str
    name: str = "RFUser"
    weight: int = 1
    fixed_count: int = 0
    verify_tls: bool | str = True
    proxy: str = ""
    no_proxy: str = ""
    wait_min: float = 1.0
    wait_max: float = 3.0
    pacing: float = 0.0
    on_start: str = ""
    on_stop: str = ""
    tasks: list[Task] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Stage:
    """Reach `users` over `seconds`."""

    seconds: float
    users: int


@dataclass
class RunConfig:
    """Run configuration. `iterations` 0 means no task limit."""

    users: int = 10
    spawn_rate: float = 1.0
    run_time: str = "30s"
    stages: list[Stage] = field(default_factory=list)
    iterations: int = 0
    stop_on_fail_ratio: float = 0.0
    fail_ratio_warmup: float = 10.0
    breaker_fails: bool = True
    stop_rules: list[StopRule] = field(default_factory=list)
    mask: frozenset[str] = frozenset()


@dataclass
class StatsRow:
    """Per-endpoint stats."""

    name: str
    request_count: int = 0
    failure_count: int = 0
    median: float = 0.0
    average: float = 0.0
    min: float = 0.0
    max: float = 0.0
    rps: float = 0.0
    failures_s: float = 0.0
    p50: float = 0.0
    p90: float = 0.0
    p95: float = 0.0
    p99: float = 0.0
    p999: float = 0.0


@dataclass
class Stats:
    """Aggregated stats."""

    rows: list[StatsRow] = field(default_factory=list)
    aggregated: StatsRow | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    fail_ratio: float = 0.0
    calls: list[str] = field(default_factory=list, repr=False)
    left_out: int = 0
    report_html: str = field(default="", repr=False)
    stopped: str = ""
    stop_failed: bool = False
    stop_machine: bool = False
    cpu_busy: bool = False
