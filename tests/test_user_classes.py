"""Several user classes share one run, as k6 scenarios do."""

from types import SimpleNamespace
from typing import Any

import pytest

import LocustLibrary as lib_module
from LocustLibrary import LocustLibrary, runner, users
from LocustLibrary.calllog import CallLog
from LocustLibrary.scenario import RunConfig, Scenario, Stats


def test_requests_go_to_the_current_class(monkeypatch) -> None:
    seen: list[list[Scenario]] = []
    monkeypatch.setattr(lib_module, "run_load_test",
                        lambda scenarios, _config: seen.append(scenarios) or Stats())
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    lib.add_get_request("home", "/")
    lib.add_user_class("token", weight=6)
    lib.set_wait_time("1s", "1s")
    lib.add_post_request("token", "/token")
    lib.run_load_test(users=1, run_time="1s")
    first, second = seen[0]
    assert [t.name for t in first.tasks] == ["home"]
    assert (second.name, second.weight, second.wait_max) == ("token", 6, 1.0)
    assert [t.name for t in second.tasks] == ["token"]
    assert second.host == first.host


def test_first_class_replaces_the_empty_default() -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1", verify_tls=False)
    lib.add_user_class("signup", weight=8)
    lib.add_get_request("register", "/r")
    lib.add_user_class("token", weight=6)
    assert [(s.name, s.weight, s.verify_tls) for s in lib._scenarios] == [
        ("signup", 8, False), ("token", 6, False)]


def test_class_needs_a_load_test() -> None:
    with pytest.raises(RuntimeError, match="Create Load Test"):
        LocustLibrary().add_user_class("token")


def test_class_carries_weight_and_count() -> None:
    scenario = Scenario(host="http://127.0.0.1", name="token", weight=6, fixed_count=2)
    user_cls = users._user_class(scenario, [])
    assert (user_cls.__name__, user_cls.weight, user_cls.fixed_count) == ("token", 6, 2)


def test_run_builds_every_class(monkeypatch) -> None:
    classes: list[Any] = []

    class Local:
        greenlet = type("G", (), {"join": lambda self, timeout=0: None})()

        def start(self, user_count: int, spawn_rate: float) -> None:
            return None

        def quit(self) -> None:
            return None

    def env(user_classes: list[Any], **_kwargs: Any) -> Any:
        classes.extend(user_classes)
        return type("Env", (), {"create_local_runner": lambda self: Local()})()

    monkeypatch.setattr(runner, "_patch_gevent", lambda: None)
    monkeypatch.setattr(runner, "_observe", lambda _env, _mask: CallLog())
    monkeypatch.setattr(runner, "_start_history", lambda _r: SimpleNamespace(kill=lambda **_k: None))
    monkeypatch.setattr(runner, "_finish", lambda _env, _calls: Stats())
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(runner, "Environment", env)
    scenarios = [Scenario(host="http://h", name="a"), Scenario(host="http://h", name="b")]
    runner.run_load_test(scenarios, RunConfig(run_time="1s"))
    assert [c.__name__ for c in classes] == ["a", "b"]
