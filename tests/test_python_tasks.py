"""Python task functions get the Locust user, so each request is its own stats row."""

import sys
import types

import pytest

from LocustLibrary import LocustLibrary, users
from LocustLibrary.scenario import Task


@pytest.fixture
def flows(monkeypatch) -> types.ModuleType:
    module = types.ModuleType("iam_flows")
    module.calls = []  # type: ignore[attr-defined]
    module.register = lambda user: module.calls.append(user)  # type: ignore[attr-defined]
    module.not_callable = 3  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "iam_flows", module)
    return module


def test_python_task_gets_the_user(flows: types.ModuleType) -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    lib.add_python_task("register", "iam_flows.register", weight=8)
    task = lib._scenario.tasks[0] if lib._scenario else Task(name="")
    user = types.SimpleNamespace()
    users._make_task_fn(task)(user)
    assert flows.calls == [user]
    assert (task.kind, task.weight) == ("py", 8)


@pytest.mark.parametrize(("target", "message"), [
    ("iam_flows.missing", "no function"),
    ("iam_flows.not_callable", "no function"),
    ("register", "module.function"),
    ("no_such_module_x.run", "No module"),
])
def test_bad_target_fails_at_add(flows: types.ModuleType, target: str, message: str) -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    with pytest.raises((ValueError, TypeError, ModuleNotFoundError), match=message):
        lib.add_python_task("x", target)


def test_python_task_needs_a_load_test() -> None:
    with pytest.raises(RuntimeError, match="Create Load Test"):
        LocustLibrary().add_python_task("x", "iam_flows.register")
