"""The emitter writes a Robot suite, a tasks module and a report a person can act on."""

import io
import json
import types
from pathlib import Path
from typing import Any

import pytest
import robot

from LocustLibrary.k6 import emit, options
from LocustLibrary.k6.scan import ExecFunction, HttpCall
from LocustLibrary.scenario import Stage

FIXTURES = Path(__file__).parent / "fixtures" / "k6"
FLOWS = [ExecFunction(n, 40, reason=f"line 41: {n[:-8]}Flow() is not an HTTP call, check or sleep")
         for n in ("signupScenario", "otpScenario", "tokenScenario")]


def _opts(name: str) -> options.K6Options:
    data = json.loads((FIXTURES / f"{name}.inspect.json").read_text(encoding="utf-8"))
    return options.parse_options(data)


@pytest.fixture(scope="module")
def combined() -> emit.Conversion:
    return emit.convert("combined.js", _opts("combined"), FLOWS)


def test_scenarios_become_weighted_classes(combined: emit.Conversion) -> None:
    assert "    Add User Class    signup    weight=8\n" in combined.robot
    assert "    Add Python Task    otpScenario    combined_tasks.otpScenario\n" in combined.robot
    assert "verify_tls=${False}" in combined.robot


def test_ramping_stages_are_summed(combined: emit.Conversion) -> None:
    assert "    Set Load Stages    120s:20    600s:20    60s:0\n" in combined.robot
    assert "    Run Load Test    max_users=${MAX_USERS}\n" in combined.robot


def test_thresholds_become_checks(combined: emit.Conversion) -> None:
    assert "    Should Meet Response Time    register    p95    1000ms\n" in combined.robot
    assert "    Should Meet Error Rate    1%    endpoint=token\n" in combined.robot


def test_flows_are_stubs_listed_in_the_report(combined: emit.Conversion) -> None:
    module = types.ModuleType("combined_tasks")
    exec(compile(combined.tasks, "combined_tasks.py", "exec"), module.__dict__)  # noqa: S102
    with pytest.raises(NotImplementedError, match="combined.js line 40"):
        module.signupScenario(object())
    assert "| scenario signup | hand port | line 41: signupFlow()" in combined.report


def test_suite_passes_robot_dryrun(combined: emit.Conversion, tmp_path: Path) -> None:
    suite = tmp_path / "combined.robot"
    suite.write_text(combined.robot, encoding="utf-8")
    out = io.StringIO()
    rc = robot.run(str(suite), dryrun=True, output=None, report=None, log=None,
                   stdout=out, stderr=out)
    assert rc == 0, out.getvalue()


def test_plain_function_becomes_client_calls() -> None:
    calls = (HttpCall("GET", "https://h/", "home"),
             HttpCall("POST", "https://h/login", "login", {"u": "a", "ok": True},
                      {"Content-Type": "application/json"}),
             HttpCall("POST", "https://h/form", "", "a=1"))
    opts = options.K6Options((options.K6Scenario("default", "shared-iterations", vus=2,
                                                 iterations=10),), (), False, 0.0, 2)
    done = emit.convert("plain.js", opts, [ExecFunction("default", 3, calls, 1.5)])
    module = types.ModuleType("plain_tasks")
    exec(compile(done.tasks, "plain_tasks.py", "exec"), module.__dict__)  # noqa: S102
    seen: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    class Client:
        def __getattr__(self, verb: str) -> Any:
            return lambda *a, **k: seen.append((verb, a, k))

    module.default(types.SimpleNamespace(client=Client()))
    assert seen[0] == ("get", ("https://h/",), {"name": "home"})
    assert seen[1][2]["json"] == {"u": "a", "ok": True}
    assert seen[2][2] == {"data": "a=1", "name": "https://h/form"}
    assert "    Set Wait Time    1.5s    1.5s\n" in done.robot
    assert "users=2    spawn_rate=2    run_time=600s    iterations=10" in done.robot
    assert "${HOST}           https://h" in done.robot


def test_arrival_rate_is_clamped_and_flagged() -> None:
    done = emit.convert("highrate.js", _opts("highrate"), FLOWS)
    assert "    Run Load Test    users=100    spawn_rate=100    run_time=600s" in done.robot
    assert "| users | clamped | 3300 users cut to max_users=100 |" in done.report
    assert "| executors | approximate |" in done.report


def test_stage_timings_that_differ_are_flagged() -> None:
    a = options.K6Scenario("a", "ramping-vus", "fa", (Stage(10, 5),))
    b = options.K6Scenario("b", "ramping-vus", "fb", (Stage(20, 5),))
    done = emit.convert("x.js", options.K6Options((a, b), (), False, 0.0, 10), [])
    assert "    Set Load Stages    10s:10\n" in done.robot
    assert "stage timings differ" in done.report
    assert "| scenario a | hand port | exec function fa not found |" in done.report


def test_big_stages_scale_down_to_the_ceiling() -> None:
    a = options.K6Scenario("a", "ramping-vus", "fa", (Stage(10, 400), Stage(10, 0)))
    done = emit.convert("x.js", options.K6Options((a,), (), False, 0.0, 400), [])
    assert "    Set Load Stages    10s:100    10s:0\n" in done.robot


def test_unsupported_threshold_is_reported() -> None:
    opts = options.K6Options((), (options.Threshold("http_req_duration", "", "avg", 300.0),
                                  options.Threshold("iterations", "", "rate", 1.0)), False, 0.0, 0)
    done = emit.convert("x.js", opts, [])
    assert "| threshold http_req_duration avg | unsupported |" in done.report
    assert "| threshold iterations rate | unsupported |" in done.report


def test_report_escapes_pipes() -> None:
    a = options.K6Scenario("a", "constant-vus", "fa", vus=1, duration_s=5)
    fn = ExecFunction("fa", 1, reason="line 2: a || b is not a call")
    done = emit.convert("x.js", options.K6Options((a,), (), False, 0.0, 1), [fn])
    assert "a // b is not a call" in done.report
