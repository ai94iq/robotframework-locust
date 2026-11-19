"""RF tasks and lifecycle keywords reach the runner."""

import pytest
from locust.event import EventHook

from LocustLibrary import LocustLibrary, runner
from LocustLibrary.scenario import Scenario, Task


def _user(hook: EventHook) -> object:
    class Events:
        request = hook

    class Env:
        events = Events()

    class User:
        environment = Env()
        client = None

    return User()


def test_rf_task_runs_the_keyword(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(runner, "_call_keyword", seen.append)
    hook = EventHook()
    fired: list[str] = []
    hook.add_listener(lambda **kw: fired.append(kw["name"]))
    task = Task(name="login", kind="rf", keyword_name="Login")
    runner._make_task_fn(task)(_user(hook))
    assert seen == ["Login"]
    assert fired == ["Login"]


def test_lifecycle_keywords_run(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(runner, "_call_keyword", seen.append)
    scenario = Scenario(
        host="http://127.0.0.1", on_start="Open", on_stop="Close"
    )
    user_cls = runner._user_class(scenario, [])
    hook = EventHook()
    user = _user(hook)
    user_cls.on_start(user)
    user_cls.on_stop(user)
    assert seen == ["Open", "Close"]


def test_blank_keyword_is_rejected() -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    for call in (
        lambda: lib.add_task("login", " "),
        lambda: lib.set_on_start(""),
        lambda: lib.set_on_stop(""),
    ):
        with pytest.raises(ValueError, match="keyword name"):
            call()
    assert lib._scenario is not None
    assert lib._scenario.tasks == []
    assert lib._scenario.on_start == ""


def test_call_keyword_uses_builtin(monkeypatch) -> None:
    seen: list[str] = []

    class FakeBuiltIn:
        def run_keyword(self, name: str) -> None:
            seen.append(name)

    monkeypatch.setattr("robot.libraries.BuiltIn.BuiltIn", FakeBuiltIn)
    runner._call_keyword("Login")
    assert seen == ["Login"]
