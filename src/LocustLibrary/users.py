"""Locust user classes built from scenarios: HTTP, RF keyword and Python tasks."""

from collections.abc import Callable
from typing import Any

from locust import HttpUser, between
from locust.exception import StopUser

from .scenario import Scenario, Task


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
    """Task runs shared by every user, like k6 shared-iterations. 0 means no limit."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.spent = 0

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
        if task.kind == "rf":
            _measure_keyword(user, task.keyword_name)
        elif task.kind == "http":
            _run_http(user, task)
        elif task.kind == "py" and task.function is not None:
            task.function(user)
        if budget is not None:
            budget.spend()

    task_fn.__name__ = task.name.replace(" ", "_") or "task"
    return task_fn


def _keyword_method(keyword_name: str) -> Callable[[Any], None]:
    def method(user: Any) -> None:
        _measure_keyword(user, keyword_name)

    return method


class _RFHttpUser(HttpUser):
    """HttpUser whose TLS check and proxy come from the scenario."""

    abstract = True
    verify_tls = True
    proxy = ""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[no-untyped-call]
        self.client.verify = self.verify_tls
        if self.proxy:
            # Locust turns off trust_env, so HTTPS_PROXY is never read on its own.
            self.client.proxies = {"http": self.proxy, "https": self.proxy}


def _user_class(scenario: Scenario, tasks: list[Any]) -> type:
    attrs: dict[str, Any] = {
        "host": scenario.host,
        "tasks": tasks,
        "weight": scenario.weight,
        "fixed_count": scenario.fixed_count,
        "verify_tls": scenario.verify_tls,
        "proxy": scenario.proxy,
        "abstract": False,
        "wait_time": between(scenario.wait_min, scenario.wait_max),
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
    return _user_class(scenario, weighted)
