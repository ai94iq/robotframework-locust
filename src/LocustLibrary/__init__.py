"""Robot Framework library for authoring and running Locust load tests in RF syntax."""

import html
import importlib
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from robot.api import logger
from robot.api.deco import keyword

from .calllog import MAX_FAILED, PER_NAME
from .runner import run_load_test
from .scenario import RunConfig, Scenario, Stage, Stats, StatsRow, Task

__version__ = "0.1.0"


def _parse_seconds(value: str) -> float:
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


_PERCENTILE_FIELDS = {
    "50": "p50",
    "90": "p90",
    "95": "p95",
    "99": "p99",
    "999": "p999",
}


def _statuses(value: object) -> tuple[int, ...]:
    parts = value if isinstance(value, list | tuple) else str(value).split(",")
    codes = tuple(int(str(p).strip()) for p in parts if str(p).strip())
    if not codes:
        raise ValueError("expected status is required")
    return codes


def _stage(text: str) -> Stage:
    try:
        duration, users = text.split(":")
        stage = Stage(seconds=_parse_seconds(duration), users=int(users))
    except ValueError as err:
        raise ValueError(f"bad stage {text!r}: use duration:users, as 2m:20") from err
    if stage.users < 0 or stage.seconds <= 0:
        raise ValueError(f"bad stage {text!r}: users and duration must be positive")
    return stage


def _python_function(target: str) -> Callable[[Any], None]:
    module_name, _, attr = target.rpartition(".")
    if not module_name:
        raise ValueError(f"use module.function, got {target!r}")
    function = getattr(importlib.import_module(module_name), attr, None)
    if not callable(function):
        raise TypeError(f"{module_name} has no function {attr!r}")
    return cast("Callable[[Any], None]", function)


def _keyword_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("keyword name is required")
    return name


def _measured_percentile(row: StatsRow, percentile: str) -> float:
    if row.request_count == 0:
        raise RuntimeError("No requests recorded.")
    field = _PERCENTILE_FIELDS.get(percentile.lower().removeprefix("p"))
    if field is None:
        raise RuntimeError(f"Percentile not measured: {percentile}")
    return float(getattr(row, field))


def _output_dir() -> str | None:
    """Robot's output folder, so reports land beside log.html; None outside a Robot run."""
    from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

    try:
        return str(BuiltIn().get_variable_value("${OUTPUT DIR}"))
    except RobotNotRunningError:
        return None


class LocustLibrary:
    """LocustLibrary drives load tests through Locust with RF-native syntax."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self, python_path: str = "") -> None:
        """`python_path` is a folder searched for the modules Add Python Task names."""
        if python_path and python_path not in sys.path:
            sys.path.insert(0, python_path)
        self._scenario: Scenario | None = None
        self._scenarios: list[Scenario] = []
        self._default: Scenario | None = None
        self._config: RunConfig | None = None
        self._stats: Stats | None = None
        self._web_proc: subprocess.Popen[bytes] | None = None
        self._dist_master: subprocess.Popen[bytes] | None = None
        self._dist_workers: list[subprocess.Popen[bytes]] | None = None

    @keyword
    def create_load_test(self, host: str, verify_tls: bool = True, proxy: str = "") -> None:
        """Create a new load test scenario.

        `verify_tls=False` matches k6 insecureSkipTLSVerify. `proxy` is an http:// proxy URL;
        Locust ignores HTTPS_PROXY, so pass it here.
        """
        from .validation import validate_host

        host = validate_host(host)
        self._scenario = Scenario(host=host, verify_tls=verify_tls, proxy=proxy)
        self._scenarios = [self._scenario]
        self._default = self._scenario
        self._config = RunConfig()
        self._stats = None

    @keyword
    def add_user_class(self, name: str, weight: int = 1, fixed_count: int = 0) -> None:
        """Start a new user class; later tasks and waits belong to it.

        One class per k6 scenario. `weight` splits the users by ratio,
        `fixed_count` pins an exact number of users.
        """
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        current = self._scenario
        self._scenario = Scenario(host=current.host, name=name, weight=weight,
                                  fixed_count=fixed_count, verify_tls=current.verify_tls,
                                  proxy=current.proxy)
        # The class Create Load Test made has no tasks yet; Locust refuses a class without tasks.
        if current is self._default and len(self._scenarios) == 1 and not current.tasks:
            self._scenarios = []
        self._scenarios.append(self._scenario)

    @keyword
    def set_load_stages(self, *stages: str) -> None:
        """Ramp like k6 ramping-vus: each `duration:users` stage, as `2m:20`."""
        if self._config is None:
            raise RuntimeError("Call Create Load Test first.")
        self._config.stages = [_stage(s) for s in stages]

    @keyword
    def set_wait_time(self, minimum: str, maximum: str) -> None:
        """Set think time between tasks."""
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.wait_min = _parse_seconds(minimum)
        self._scenario.wait_max = _parse_seconds(maximum)

    @keyword
    def add_get_request(self, name: str, path: str, weight: int = 1,
                        expected_status: object = 200,
                        headers: dict[str, str] | None = None) -> None:
        """Add a GET request task.

        `expected_status` takes one code, a comma list (`200, 204`) or a list.
        """
        self._add_http_task(Task(name=name, method="GET", path=path, weight=weight,
                                 expected=_statuses(expected_status),
                                 headers=headers or {}))

    @keyword
    def add_post_request(self, name: str, path: str, weight: int = 1,
                         expected_status: object = 200,
                         headers: dict[str, str] | None = None,
                         json: object = None, data: object = None) -> None:
        """Add a POST request task with a `json` or form `data` body."""
        self._add_http_task(Task(name=name, method="POST", path=path, weight=weight,
                                 expected=_statuses(expected_status),
                                 headers=headers or {}, json=json, body=data))

    @keyword
    def add_task(self, name: str, keyword: str = "", weight: int = 1) -> None:
        """Add an RF-keyword task."""
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.tasks.append(
            Task(name=name, kind="rf", weight=weight, keyword_name=_keyword_name(keyword))
        )

    @keyword
    def add_python_task(self, name: str, function: str, weight: int = 1) -> None:
        """Add a Python task: `module.function` called with the Locust user.

        Requests made through `user.client` show as their own stats rows, so a
        multi-step flow (register, read OTP, verify) is measured per request.
        """
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.tasks.append(
            Task(name=name, kind="py", weight=weight, function=_python_function(function))
        )

    @keyword
    def set_on_start(self, keyword_name: str) -> None:
        """Set the on_start keyword name."""
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.on_start = _keyword_name(keyword_name)

    @keyword
    def set_on_stop(self, keyword_name: str) -> None:
        """Set the on_stop keyword name."""
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.on_stop = _keyword_name(keyword_name)

    def _add_http_task(self, task: Task) -> None:
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.tasks.append(task)

    @keyword
    def run_load_test(self, users: int = 10, spawn_rate: float = 1.0,
                      run_time: str = "30s", iterations: int = 0,
                      max_users: int = 100) -> None:
        """Run the configured load test headless.

        `iterations` stops every user after that many task runs in total, within `run_time`.
        Stages from Set Load Stages replace `users`, `spawn_rate` and `run_time`.
        A run that would start more than `max_users` users is refused before it starts.
        The log gets a stats table and the first calls of every request name plus the failed ones.
        """
        if self._scenario is None or self._config is None:
            raise RuntimeError("Call Create Load Test first.")
        self._config.users = users
        self._config.spawn_rate = spawn_rate
        self._config.run_time = run_time
        self._config.iterations = iterations
        self._check_ceiling(self._config, max_users)
        for host in dict.fromkeys(s.host for s in self._scenarios if not s.verify_tls):
            logger.warn(f"TLS verification is off for {host}")
        self._stats = run_load_test(self._scenarios, self._config)
        self._log_run(self._stats)

    def _log_run(self, stats: Stats) -> None:
        from .reporting import stats_table_html

        logger.info(stats_table_html(stats), html=True)
        for block in stats.calls:
            logger.info(block, html=True)
        if stats.left_out:
            logger.info(f"{stats.left_out} more calls not logged: the log keeps the first "
                        f"{PER_NAME} of each request name and up to {MAX_FAILED} failures.")

    def _check_ceiling(self, config: RunConfig, max_users: int) -> None:
        peak = max((s.users for s in config.stages), default=config.users)
        peak = max(peak, sum(s.fixed_count for s in self._scenarios))
        if peak > max_users:
            raise ValueError(f"{peak} users is over max_users={max_users}; raise it on purpose")

    @keyword
    def get_locust_stats(self) -> dict[str, object]:
        """Return parsed stats as a dict."""
        if self._stats is None:
            return {}
        return {"rows": [r.__dict__ for r in self._stats.rows],
                "aggregated": self._stats.aggregated.__dict__ if self._stats.aggregated else None,
                "fail_ratio": self._stats.fail_ratio}

    @keyword
    def get_aggregated_stats(self) -> dict[str, object]:
        """Return aggregated stats."""
        if self._stats is None or self._stats.aggregated is None:
            return {}
        return self._stats.aggregated.__dict__

    def _aggregated(self) -> StatsRow:
        stats = self._stats
        if stats is None or stats.aggregated is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        if stats.aggregated.request_count == 0:
            raise RuntimeError("No requests recorded.")
        return stats.aggregated

    @keyword
    def should_have_no_failures(self) -> None:
        """Fail if any request failed."""
        row = self._aggregated()
        if row.failure_count > 0:
            raise AssertionError(f"Failures: {row.failure_count}")

    @keyword
    def should_meet_response_time(self, endpoint: str, percentile: str,
                                  maximum: str) -> None:
        """Assert response time percentile <= maximum."""
        if self._stats is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        if maximum.lower().endswith("ms"):
            max_ms = float(maximum.lower().rstrip("ms"))
        else:
            max_ms = _parse_seconds(maximum) * 1000
        # One name can hold several methods; the slowest one decides.
        targets = [r for r in self._stats.rows if r.name == endpoint]
        if not targets and self._stats.aggregated and endpoint.lower() in ("aggregated", "total", ""):
            targets = [self._stats.aggregated]
        if not targets:
            raise RuntimeError(f"Endpoint not found: {endpoint}")
        actual = max(_measured_percentile(r, percentile) for r in targets)
        if actual > max_ms:
            raise AssertionError(
                f"{endpoint} {percentile}={actual}ms > {max_ms}ms"
            )

    @keyword
    def should_meet_throughput(self, minimum: str) -> None:
        """Assert RPS >= minimum."""
        row = self._aggregated()
        min_rps = float(minimum)
        if row.rps < min_rps:
            raise AssertionError(f"RPS {row.rps} < {min_rps}")

    @keyword
    def should_meet_error_rate(self, maximum: str, endpoint: str = "") -> None:
        """Assert error rate <= maximum percent, overall or for one endpoint."""
        rows = self._endpoint_rows(endpoint) if endpoint else [self._aggregated()]
        max_rate = float(maximum.rstrip("%")) / 100.0
        rate = sum(r.failure_count for r in rows) / sum(r.request_count for r in rows)
        if rate > max_rate:
            raise AssertionError(f"{rows[0].name} error rate {rate:.2%} > {max_rate:.2%}")

    def _endpoint_rows(self, endpoint: str) -> list[StatsRow]:
        # One name can hold several methods; k6 thresholds count them together.
        rows = [r for r in (self._stats.rows if self._stats else []) if r.name == endpoint]
        if not rows:
            raise RuntimeError(f"Endpoint not found: {endpoint}")
        if sum(r.request_count for r in rows) == 0:
            raise RuntimeError("No requests recorded.")
        return rows

    @keyword
    def export_report(self, base_path: str = "locust") -> str:
        """Write <base>_stats.csv and the Locust HTML report <base>.html beside log.html.

        The HTML report is linked in the log. Returns the base path.
        """
        if self._stats is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        from .reporting import write_stats_csv

        base = write_stats_csv(self._stats, base_path, _output_dir())
        if self._stats.report_html:
            Path(base + ".html").write_text(self._stats.report_html, encoding="utf-8")
            name = html.escape(Path(base).name + ".html")
            logger.info(f'Locust report: <a href="{name}">{name}</a>', html=True)
        return base

    @keyword
    def start_locust_web(self, locustfile: str, port: int = 8089) -> None:
        """Start Locust web UI as subprocess."""
        from .webui import start_web_ui, stop_web_ui

        if self._web_proc is not None:
            stop_web_ui(self._web_proc)
        self._web_proc = start_web_ui(locustfile, port=port)

    @keyword
    def stop_locust_web(self) -> None:
        """Stop Locust web UI."""
        from .webui import stop_web_ui

        proc = self._web_proc
        if proc is not None:
            stop_web_ui(proc)
            self._web_proc = None

    @keyword
    def run_distributed(self, locustfile: str, processes: int = 2) -> None:
        """Run Locust in distributed mode."""
        from .distributed import run_distributed as _run

        self.stop_distributed()
        self._dist_master, self._dist_workers = _run(
            locustfile, processes=processes
        )

    @keyword
    def stop_distributed(self) -> None:
        """Stop the master and workers from Run Distributed."""
        from .distributed import stop_distributed as _stop

        _stop(self._dist_master, self._dist_workers)
        self._dist_master = None
        self._dist_workers = None
