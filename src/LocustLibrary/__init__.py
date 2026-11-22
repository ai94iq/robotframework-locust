"""Robot Framework library for authoring and running Locust load tests in RF syntax."""

import subprocess
import sys

from robot.api import logger
from robot.api.deco import keyword

from .builder import BuildKeywords
from .calllog import MAX_FAILED, PER_NAME, masked_names
from .checks import CheckKeywords
from .parsing import _parse_seconds, _ratio
from .runner import run_load_test
from .scenario import RunConfig, Scenario, Stats
from .shared import SharedKeywords

__version__ = "1.0.3"


def _target_args(host: str, allowed_hosts: str) -> list[str]:
    """Locust --host args for a target checked like Create Load Test; none without a host."""
    from .validation import allowed_hosts as read_allowed
    from .validation import validate_host

    if not host:
        return []
    allowed = read_allowed(allowed_hosts)
    host = validate_host(host, allowed)
    if not allowed:
        logger.warn(f"No allowed hosts set; {host} is not checked against a list")
    return ["--host", host]


class LocustLibrary(BuildKeywords, CheckKeywords, SharedKeywords):
    """LocustLibrary drives load tests through Locust with RF-native syntax."""

    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self, python_path: str = "", shared_limit: int = 10000, mask: str = "") -> None:
        """`python_path` is a folder searched for the modules Add Python Task names.

        `shared_limit` caps the values one Put Shared Value name holds; 0 is no limit.
        `mask` is a comma list of extra header or body field names to mask in the request log.
        """
        self._mask = masked_names(mask)
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
        self._shared = {}
        self._shared_limit = shared_limit

    @keyword
    def run_load_test(self, users: int = 10, spawn_rate: float = 1.0,
                      run_time: str = "30s", iterations: int = 0,
                      max_users: int = 100, stop_on_fail_ratio: str = "0",
                      fail_ratio_warmup: str = "10s", breaker_fails: bool = True,
                      fail_on_busy_cpu: bool = False) -> None:
        """Run the configured load test headless.

        `iterations` stops every user after that many task runs in total, within `run_time`.
        Stages from Set Load Stages replace `users`, `spawn_rate` and `run_time`.
        A run that would start more than `max_users` users is refused before it starts.
        The log gets a stats table and the first calls of every request name plus the failed ones.
        `stop_on_fail_ratio` (`20%` or `0.2`; 0 is off) stops the run early once the share of
        failed requests passes it after `fail_ratio_warmup`; the reason is logged as a warning.
        A breaker stop fails the keyword like a stop rule; `breaker_fails=False` lets it pass.
        A load generator CPU over 90% is a warning; `fail_on_busy_cpu=True` fails the keyword.
        """
        if self._scenario is None or self._config is None:
            raise RuntimeError("Call Create Load Test first.")
        self._config.users = users
        self._config.spawn_rate = spawn_rate
        self._config.run_time = run_time
        self._config.iterations = iterations
        self._config.stop_on_fail_ratio = _ratio(stop_on_fail_ratio)
        self._config.fail_ratio_warmup = _parse_seconds(fail_ratio_warmup)
        self._config.breaker_fails = breaker_fails
        self._config.mask = self._mask
        self._check_ceiling(self._config, max_users)
        self._shared.clear()
        for host in dict.fromkeys(s.host for s in self._scenarios if not s.verify_tls):
            logger.warn(f"TLS verification is off for {host}")
        self._stats = run_load_test(self._scenarios, self._config)
        if self._stats.stopped:
            logger.warn(f"Load test {self._stats.stopped}")
        if self._stats.cpu_busy:
            logger.warn("Load generator CPU went over 90%; response times may be too high")
        self._log_run(self._stats)
        if self._stats.stop_failed and self._stats.stop_machine:
            raise AssertionError(f"Inconclusive: the load machine ran out of room, so the target was not judged; "
                                 f"load test {self._stats.stopped}")
        if self._stats.stop_failed:
            raise AssertionError(f"Load test {self._stats.stopped}")
        if fail_on_busy_cpu and self._stats.cpu_busy:
            raise AssertionError("Load generator CPU went over 90%; response times are not reliable")

    @keyword
    def get_user_index(self) -> int:
        """Return the number of the virtual user running this task, unique within the run.

        Use it for a unique value or a data row per user, such as `${PREFIX}_${index}`.
        """
        from .users import current_user

        return int(current_user().index)

    @keyword
    def get_user_iteration(self) -> int:
        """Return how many task runs this virtual user has started, counting this one."""
        from .users import current_user

        return int(current_user().iteration)

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
        fixed = sum(s.fixed_count for s in self._scenarios)
        if fixed > peak:
            logger.warn(f"Fixed counts add up to {fixed}, but only {peak} users run; "
                        "fixed classes take them first")
        if peak > max_users:
            raise ValueError(f"{peak} users is over max_users={max_users}; raise it on purpose")

    @keyword
    def start_locust_web(self, locustfile: str, port: int = 8089, host: str = "",
                         allowed_hosts: str = "") -> None:
        """Start Locust web UI as subprocess.

        `host` is the target URL, checked against `allowed_hosts` (or
        LOCUSTLIBRARY_ALLOWED_HOSTS) like Create Load Test.
        """
        from .webui import start_web_ui, stop_web_ui

        extra = _target_args(host, allowed_hosts)
        if self._web_proc is not None:
            stop_web_ui(self._web_proc)
        self._web_proc = start_web_ui(locustfile, port=port, extra=extra)

    @keyword
    def stop_locust_web(self) -> None:
        """Stop Locust web UI."""
        from .webui import stop_web_ui

        proc = self._web_proc
        if proc is not None:
            stop_web_ui(proc)
            self._web_proc = None

    @keyword
    def run_distributed(self, locustfile: str, processes: int = 2, host: str = "",
                        allowed_hosts: str = "", users: int = 0,
                        max_users: int = 100) -> None:
        """Run Locust in distributed mode.

        `host` is checked like Create Load Test; `users` above `max_users` is refused.
        """
        from .distributed import run_distributed as _run

        extra = _target_args(host, allowed_hosts)
        if users > max_users:
            raise ValueError(f"{users} users is over max_users={max_users}; raise it on purpose")
        if users:
            extra += ["--users", str(users), "--autostart"]
        self.stop_distributed()
        self._dist_master, self._dist_workers = _run(
            locustfile, processes=processes, extra=extra
        )

    @keyword
    def stop_distributed(self) -> None:
        """Stop the master and workers from Run Distributed."""
        from .distributed import stop_distributed as _stop

        _stop(self._dist_master, self._dist_workers)
        self._dist_master = None
        self._dist_workers = None
