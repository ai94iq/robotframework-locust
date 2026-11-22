"""Locust user classes built from scenarios: HTTP, RF keyword and Python tasks."""

from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

import gevent.local
from locust import HttpUser, between, constant_pacing
from locust.exception import StopUser

from .scenario import Scenario, Task

# Every user runs in its own greenlet, so this holds the user whose task is running now.
_running = gevent.local.local()


def current_user() -> Any:
    user = getattr(_running, "user", None)
    if user is None:
        raise RuntimeError("This keyword works only inside a load test task.")
    return user


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
        if response.status_code not in task.expected:
            response.failure(f"status {response.status_code} not in {list(task.expected)}")
        elif task.expected_text and task.expected_text not in (response.text or ""):
            # A 200 carrying an error page would otherwise count as a success.
            response.failure(f"expected text '{task.expected_text}' not in the body")
        else:
            response.success()


class Budget:
    """Run-wide counts shared by every user: task runs (like k6 shared-iterations; 0 means
    no limit) and user numbers."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.spent = 0
        self.users = 0

    def next_user(self) -> int:
        self.users += 1
        return self.users

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
        user.iteration = getattr(user, "iteration", 0) + 1
        _running.user = user
        try:
            _run_task(user, task)
        finally:
            _running.user = None
        if budget is not None:
            budget.spend()

    task_fn.__name__ = task.name.replace(" ", "_") or "task"
    return task_fn


def _run_task(user: Any, task: Task) -> None:
    if task.kind == "rf":
        _measure_keyword(user, task.keyword_name)
    elif task.kind == "http":
        _run_http(user, task)
    elif task.kind == "py" and task.function is not None:
        task.function(user)


def _keyword_method(keyword_name: str) -> Callable[[Any], None]:
    def method(user: Any) -> None:
        _running.user = user
        try:
            _measure_keyword(user, keyword_name)
        finally:
            _running.user = None

    return method


def _bypassed(url: str, rules: list[str]) -> bool:
    """no_proxy as curl reads it: a name matches itself and its subdomains; name:port only that port."""
    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    port = parts.port or (443 if parts.scheme == "https" else 80)
    for rule in rules:
        name, sep, wanted = rule.rpartition(":")
        if not (sep and wanted.isdigit()):
            name, wanted = rule, ""
        name = name.lstrip(".")
        if (host == name or host.endswith("." + name)) and (not wanted or int(wanted) == port):
            return True
    return False


def _bypass_suffixes(client: Any, no_proxy: str) -> None:
    """Send no_proxy hosts direct, with .suffix and host:port forms the proxies dict cannot hold."""
    rules = [h.strip().lower() for h in no_proxy.split(",") if h.strip()]
    if not rules:
        return
    merge = client.merge_environment_settings

    def direct(url: str, *args: Any) -> Any:
        settings = merge(url, *args)
        if _bypassed(url, rules):
            settings["proxies"] = {}
        return settings

    client.merge_environment_settings = direct


class _RFHttpUser(HttpUser):
    """HttpUser whose TLS check and proxy come from the scenario."""

    abstract = True
    verify_tls = True
    proxy = ""
    no_proxy = ""
    budget: Budget | None = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[no-untyped-call]
        self.index = self.budget.next_user() if self.budget else 0
        self.iteration = 0
        self.client.verify = self.verify_tls
        if self.proxy:
            # Locust turns off trust_env, so HTTPS_PROXY is never read on its own.
            proxies: dict[str, str | None] = {"http": self.proxy, "https": self.proxy}
            for host in filter(None, (h.strip().lower() for h in self.no_proxy.split(","))):
                # A scheme://host key beats the scheme key; None sends that host direct.
                proxies[f"http://{host}"] = proxies[f"https://{host}"] = None
            self.client.proxies = proxies  # type: ignore[assignment]
            _bypass_suffixes(self.client, self.no_proxy)


def _user_class(scenario: Scenario, tasks: list[Any], budget: Budget | None = None) -> type:
    attrs: dict[str, Any] = {
        "budget": budget,
        "host": scenario.host,
        "tasks": tasks,
        "weight": scenario.weight,
        "fixed_count": scenario.fixed_count,
        "verify_tls": scenario.verify_tls,
        "proxy": scenario.proxy,
        "no_proxy": scenario.no_proxy,
        "abstract": False,
        "wait_time": (constant_pacing(scenario.pacing) if scenario.pacing
                      else between(scenario.wait_min, scenario.wait_max)),
    }
    if scenario.on_start:
        attrs["on_start"] = _keyword_method(scenario.on_start)
    if scenario.on_stop:
        attrs["on_stop"] = _keyword_method(scenario.on_stop)
    return type(scenario.name, (_RFHttpUser,), attrs)


def build_class(scenario: Scenario, budget: Budget) -> type:
    weighted: list[Any] = []
    for task in scenario.tasks:
        weighted.extend([_make_task_fn(task, budget)] * max(1, task.weight))
    return _user_class(scenario, weighted, budget)
