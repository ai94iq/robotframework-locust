"""Keywords that build the load test: classes, stages, waits and tasks."""

from robot.api import logger
from robot.api.deco import keyword

from .parsing import _keyword_name, _parse_seconds, _python_function, _stage, _statuses
from .scenario import RunConfig, Scenario, Stats, Task


class BuildKeywords:
    """Keywords that fill the scenarios a run starts from."""

    _scenario: Scenario | None
    _scenarios: list[Scenario]
    _default: Scenario | None
    _config: RunConfig | None
    _stats: Stats | None

    @keyword
    def create_load_test(self, host: str, verify_tls: bool = True, proxy: str = "",
                         allowed_hosts: str = "") -> None:
        """Create a new load test scenario.

        `verify_tls=False` matches k6 insecureSkipTLSVerify. `proxy` is an http:// proxy URL;
        Locust ignores HTTPS_PROXY, so pass it here.
        `allowed_hosts` is a comma list of host names the test may hit; when it is empty the
        LOCUSTLIBRARY_ALLOWED_HOSTS environment variable is used. A host outside the list is
        refused. With no list at all the host is accepted and one warning is logged.
        """
        from .validation import allowed_hosts as read_allowed
        from .validation import validate_host

        allowed = read_allowed(allowed_hosts)
        host = validate_host(host, allowed)
        if not allowed:
            logger.warn(f"No allowed hosts set; {host} is not checked against a list")
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
    def add_stop_rule(self, rule: str) -> None:
        """Stop the run once `rule` holds for its whole window, like `p95 > 1s for 10s`.

        Metrics: `pN` (Locust's last 10 s window), `fail` and `rcNNN` (`?` and `*` match a
        digit; share since the last check), `cpu` and `mem` (load machine). End with
        `, stop as passed` to stop without failing; the default fails Run Load Test.
        """
        from .stoprules import parse_rule

        if self._config is None:
            raise RuntimeError("Call Create Load Test first.")
        self._config.stop_rules.append(parse_rule(rule))

    @keyword
    def add_get_request(self, name: str, path: str, weight: int = 1,
                        expected_status: object = 200,
                        headers: dict[str, str] | None = None,
                        expected_text: str = "") -> None:
        """Add a GET request task.

        `expected_status` takes one code, a comma list (`200, 204`) or a list.
        `expected_text` must appear in the response body, or the request counts as failed.
        """
        self._add_http_task(Task(name=name, method="GET", path=path, weight=weight,
                                 expected=_statuses(expected_status),
                                 headers=headers or {}, expected_text=expected_text))

    @keyword
    def add_post_request(self, name: str, path: str, weight: int = 1,
                         expected_status: object = 200,
                         headers: dict[str, str] | None = None,
                         json: object = None, data: object = None,
                         expected_text: str = "") -> None:
        """Add a POST request task with a `json` or form `data` body.

        `expected_text` must appear in the response body, or the request counts as failed.
        """
        self._add_http_task(Task(name=name, method="POST", path=path, weight=weight,
                                 expected=_statuses(expected_status),
                                 headers=headers or {}, json=json, body=data,
                                 expected_text=expected_text))

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
