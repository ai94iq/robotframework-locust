"""Each virtual user knows its own number and task run count, even while others run."""

from typing import Any

import gevent
import pytest
from locust.env import Environment

from LocustLibrary import LocustLibrary, users
from LocustLibrary.scenario import Scenario, Task
from LocustLibrary.users import Budget, build_class


def _scenario(name: str, task: Task) -> Scenario:
    return Scenario(host="http://127.0.0.1", name=name, tasks=[task])


def test_users_are_numbered_across_classes() -> None:
    budget, env = Budget(0), Environment()
    task = Task(name="noop", kind="py", function=lambda _user: None)
    first = build_class(_scenario("first", task), budget)(env)
    second = build_class(_scenario("second", task), budget)(env)
    assert (first.index, second.index) == (1, 2)


def test_iteration_counts_each_task_run() -> None:
    seen: list[int] = []
    task = Task(name="note", kind="py", function=lambda user: seen.append(user.iteration))
    user_class = build_class(_scenario("one", task), Budget(0))
    user = user_class(Environment())
    user.tasks[0](user)
    user.tasks[0](user)
    assert seen == [1, 2]


def test_keywords_read_their_own_user(monkeypatch: pytest.MonkeyPatch) -> None:
    lib, seen = LocustLibrary(), []

    def keyword(_name: str) -> None:
        index = lib.get_user_index()
        gevent.sleep(0)  # let the other user run in between, as a real request would
        seen.append((index, lib.get_user_index(), lib.get_user_iteration()))

    monkeypatch.setattr(users, "_call_keyword", keyword)
    user_class = build_class(_scenario("rf", Task(name="login", kind="rf", keyword_name="Login")), Budget(0))
    pair: list[Any] = [user_class(Environment()), user_class(Environment())]
    gevent.joinall([gevent.spawn(u.tasks[0], u) for u in pair])
    assert sorted(seen) == [(1, 1, 1), (2, 2, 1)]


def test_user_keywords_need_a_running_user() -> None:
    with pytest.raises(RuntimeError, match="inside a load test task"):
        LocustLibrary().get_user_index()
