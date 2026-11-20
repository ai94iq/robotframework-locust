"""Robot Framework library for authoring and running Locust load tests in RF syntax."""

import subprocess

from robot.api import logger
from robot.api.deco import keyword

from .runner import run_load_test
from .scenario import RunConfig, Scenario, Stats, StatsRow, Task

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


class LocustLibrary:
    """LocustLibrary drives load tests through Locust with RF-native syntax."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self) -> None:
        self._scenario: Scenario | None = None
        self._config: RunConfig | None = None
        self._stats: Stats | None = None
        self._web_proc: subprocess.Popen[bytes] | None = None
        self._dist_master: subprocess.Popen[bytes] | None = None
        self._dist_workers: list[subprocess.Popen[bytes]] | None = None

    @keyword
    def create_load_test(self, host: str) -> None:
        """Create a new load test scenario."""
        from .validation import validate_host

        host = validate_host(host)
        self._scenario = Scenario(host=host)
        self._config = RunConfig()
        self._stats = None

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
                      run_time: str = "30s", csv_prefix: str = "locust") -> None:
        """Run the configured load test headless."""
        if self._scenario is None or self._config is None:
            raise RuntimeError("Call Create Load Test first.")
        self._config.users = users
        self._config.spawn_rate = spawn_rate
        self._config.run_time = run_time
        from .validation import sanitize_prefix

        self._config.csv_prefix = sanitize_prefix(csv_prefix)
        self._stats = run_load_test(self._scenario, self._config)
        logger.info(f"Load test finished: {self._stats}")

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
        target = None
        for r in self._stats.rows:
            if r.name == endpoint:
                target = r
                break
        if target is None and self._stats.aggregated and endpoint.lower() in ("aggregated", "total", ""):
            target = self._stats.aggregated
        if target is None:
            raise RuntimeError(f"Endpoint not found: {endpoint}")
        actual = _measured_percentile(target, percentile)
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
    def should_meet_error_rate(self, maximum: str) -> None:
        """Assert error rate <= maximum percent."""
        row = self._aggregated()
        max_rate = float(maximum.rstrip("%")) / 100.0
        rate = row.failure_count / row.request_count
        if rate > max_rate:
            raise AssertionError(f"Error rate {rate:.2%} > {max_rate:.2%}")

    @keyword
    def export_report(self, base_path: str = "locust") -> str:
        """Export CSV report. Returns base path."""
        if self._stats is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        from .reporting import write_stats_csv

        return write_stats_csv(self._stats, base_path)

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
