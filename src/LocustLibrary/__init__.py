"""Robot Framework library for authoring and running Locust load tests in RF syntax."""

from robot.api import logger
from robot.api.deco import keyword

from .scenario import Scenario, Task, RunConfig
from .runner import run_load_test

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


class LocustLibrary:
    """LocustLibrary drives load tests through Locust with RF-native syntax."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self) -> None:
        self._scenario: Scenario | None = None
        self._config: RunConfig | None = None
        self._stats = None

    @keyword
    def create_load_test(self, host: str) -> None:
        """Create a new load test scenario."""
        self._scenario = Scenario(host=host)
        self._config = RunConfig()

    @keyword
    def set_wait_time(self, minimum: str, maximum: str) -> None:
        """Set think time between tasks."""
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.wait_min = _parse_seconds(minimum)
        self._scenario.wait_max = _parse_seconds(maximum)

    @keyword
    def add_get_request(self, name: str, path: str, weight: int = 1,
                        expected_status: int = 200) -> None:
        """Add a GET request task."""
        self._add_http_task(name, "GET", path, weight, expected_status)

    @keyword
    def add_post_request(self, name: str, path: str, weight: int = 1,
                         expected_status: int = 200) -> None:
        """Add a POST request task."""
        self._add_http_task(name, "POST", path, weight, expected_status)

    @keyword
    def add_task(self, name: str, keyword: str = "", weight: int = 1) -> None:
        """Add an RF-keyword task."""
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.tasks.append(
            Task(name=name, kind="rf", weight=weight, keyword_name=keyword)
        )

    @keyword
    def set_on_start(self, keyword_name: str) -> None:
        """Set the on_start keyword name."""
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.on_start = keyword_name

    @keyword
    def set_on_stop(self, keyword_name: str) -> None:
        """Set the on_stop keyword name."""
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.on_stop = keyword_name

    def _add_http_task(self, name, method, path, weight, expected_status):
        if self._scenario is None:
            raise RuntimeError("Call Create Load Test first.")
        self._scenario.tasks.append(
            Task(name=name, kind="http", method=method, path=path,
                 weight=weight, expected_status=expected_status)
        )

    @keyword
    def run_load_test(self, users: int = 10, spawn_rate: float = 1.0,
                      run_time: str = "30s", csv_prefix: str = "locust") -> None:
        """Run the configured load test headless."""
        if self._scenario is None or self._config is None:
            raise RuntimeError("Call Create Load Test first.")
        self._config.users = users
        self._config.spawn_rate = spawn_rate
        self._config.run_time = run_time
        self._config.csv_prefix = csv_prefix
        self._stats = run_load_test(self._scenario, self._config)
        logger.info(f"Load test finished: {self._stats}")

    @keyword
    def get_locust_stats(self) -> dict:
        """Return parsed stats as a dict."""
        if self._stats is None:
            return {}
        return {"rows": [r.__dict__ for r in self._stats.rows],
                "aggregated": self._stats.aggregated.__dict__ if self._stats.aggregated else None,
                "fail_ratio": self._stats.fail_ratio}

    @keyword
    def get_aggregated_stats(self) -> dict:
        """Return aggregated stats."""
        if self._stats is None or self._stats.aggregated is None:
            return {}
        return self._stats.aggregated.__dict__

    @keyword
    def should_have_no_failures(self) -> None:
        """Fail if any request failed."""
        if self._stats is None or self._stats.aggregated is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        if self._stats.aggregated.failure_count > 0:
            raise AssertionError(
                f"Failures: {self._stats.aggregated.failure_count}"
            )

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
        p = percentile.lower().replace("p", "")
        target = None
        for r in self._stats.rows:
            if r.name == endpoint:
                target = r
                break
        if target is None and self._stats.aggregated and endpoint.lower() in ("aggregated", "total", ""):
            target = self._stats.aggregated
        if target is None:
            raise RuntimeError(f"Endpoint not found: {endpoint}")
        attr = "p" + p
        actual = getattr(target, attr, 0.0)
        if actual > max_ms:
            raise AssertionError(
                f"{endpoint} {percentile}={actual}ms > {max_ms}ms"
            )

    @keyword
    def should_meet_throughput(self, minimum: str) -> None:
        """Assert RPS >= minimum."""
        if self._stats is None or self._stats.aggregated is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        min_rps = float(minimum)
        if self._stats.aggregated.rps < min_rps:
            raise AssertionError(
                f"RPS {self._stats.aggregated.rps} < {min_rps}"
            )

    @keyword
    def should_meet_error_rate(self, maximum: str) -> None:
        """Assert error rate <= maximum percent."""
        if self._stats is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        max_rate = float(maximum.rstrip("%")) / 100.0
        if self._stats.fail_ratio > max_rate:
            raise AssertionError(
                f"Error rate {self._stats.fail_ratio:.2%} > {max_rate:.2%}"
            )
