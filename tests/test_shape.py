"""Ramp stages and an iteration budget, as k6 runs them."""

from typing import Any

import pytest
from locust.exception import StopUser

from LocustLibrary import LocustLibrary, runner
from LocustLibrary.scenario import RunConfig, Scenario, Stats, Task
from LocustLibrary.shape import Stage, StageShape


def _shape_at(seconds: float) -> Any:
    shape = StageShape([Stage(120, 20), Stage(600, 20), Stage(60, 0)])
    shape.get_run_time = lambda: seconds  # type: ignore[method-assign]
    return shape.tick()


@pytest.mark.parametrize(("seconds", "tick"), [
    (0, (20, pytest.approx(20 / 120))),
    (300, (20, 1.0)),
    (750, (0, pytest.approx(20 / 60))),
    (781, None),
])
def test_stage_ticks_ramp_hold_down(seconds: float, tick: object) -> None:
    assert _shape_at(seconds) == tick


def test_stage_total_seconds() -> None:
    assert StageShape([Stage(1, 2), Stage(3, 0)]).total == 4


def test_keyword_parses_stages() -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    lib.set_load_stages("2m:8", "10m:8", "1m:0")
    assert lib._config is not None
    assert lib._config.stages == [Stage(120, 8), Stage(600, 8), Stage(60, 0)]


@pytest.mark.parametrize("bad", ["2m", "x:1", "1m:-1"])
def test_bad_stage_is_rejected(bad: str) -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    with pytest.raises(ValueError, match="stage"):
        lib.set_load_stages(bad)


def test_stages_need_a_load_test() -> None:
    with pytest.raises(RuntimeError, match="Create Load Test"):
        LocustLibrary().set_load_stages("1s:1")


def test_budget_stops_users_after_n_tasks(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(runner, "_call_keyword", seen.append)
    budget = runner.Budget(2)
    task_fn = runner._make_task_fn(Task(name="t", kind="rf", keyword_name="K"), budget)

    class User:
        environment = type("E", (), {"events": type("V", (), {"request": _hook()})()})()

    task_fn(User())
    task_fn(User())
    assert budget.done
    with pytest.raises(StopUser):
        task_fn(User())
    assert seen == ["K", "K"]


def test_no_budget_never_stops() -> None:
    budget = runner.Budget(0)
    budget.spend()
    assert not budget.done


def _hook() -> Any:
    from locust.event import EventHook

    return EventHook()


def _fake_env(started: list[str]) -> Any:
    class Local:
        greenlet = type("G", (), {"join": lambda self, timeout=0: None})()

        def start(self, user_count: int, spawn_rate: float) -> None:
            started.append("start")

        def start_shape(self) -> None:
            started.append("shape")

        def quit(self) -> None:
            started.append("quit")

    def env(user_classes: list[Any], shape_class: Any = None) -> Any:
        started.append("with shape" if shape_class else "no shape")
        return type("Env", (), {"create_local_runner": lambda self: Local()})()

    return env


@pytest.mark.parametrize(("config", "expected"), [
    (RunConfig(run_time="1s"), ["no shape", "start", "quit"]),
    (RunConfig(stages=[Stage(1, 1)]), ["with shape", "shape", "quit"]),
])
def test_run_uses_shape_when_staged(monkeypatch, config: RunConfig, expected: list[str]) -> None:
    started: list[str] = []
    monkeypatch.setattr(runner, "_patch_gevent", lambda: None)
    monkeypatch.setattr(runner, "_stats_from_env", lambda _env: Stats())
    monkeypatch.setattr(runner, "Environment", _fake_env(started))
    monkeypatch.setattr(runner.time, "sleep", lambda _s: None)
    runner.run_load_test([Scenario(host="http://h")], config)
    assert started == expected


def test_run_ends_early_when_budget_spent(monkeypatch) -> None:
    clock = iter(range(100))
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runner.time, "sleep", lambda _s: None)
    budget = runner.Budget(1)
    budget.spend()
    runner._wait_until(10, budget)
    assert next(clock) < 5


def test_run_waits_out_the_time_when_budget_left(monkeypatch) -> None:
    clock = iter([0, 0, 1, 2, 3])
    slept: list[float] = []
    monkeypatch.setattr(runner.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(runner.time, "sleep", slept.append)
    runner._wait_until(2, runner.Budget(5))
    assert slept == [0.5, 0.5]


def test_iterations_reach_the_config(monkeypatch) -> None:
    configs: list[RunConfig] = []
    import LocustLibrary as lib_module

    monkeypatch.setattr(lib_module, "run_load_test",
                        lambda _s, config: configs.append(config) or Stats())
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    lib.run_load_test(users=10, run_time="10m", iterations=5000)
    assert configs[0].iterations == 5000
