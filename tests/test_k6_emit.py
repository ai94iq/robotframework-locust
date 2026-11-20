"""The emitter writes a four-layer Robot project that passes dryrun and Robocop."""

import io
import json
import subprocess
import sys
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


def _keywords(done: emit.Conversion, stem: str) -> str:
    return done.files[f"collections/{stem}_test_keywords.resource"]


def _tasks(done: emit.Conversion, stem: str) -> types.ModuleType:
    module = types.ModuleType(f"{stem}_tasks")
    source = done.files[f"resources/python/{stem}_tasks.py"]
    exec(compile(source, f"{stem}_tasks.py", "exec"), module.__dict__)  # noqa: S102
    return module


def test_layout_has_thin_suite_and_keywords(combined: emit.Conversion) -> None:
    assert sorted(combined.files) == ["collections/combined_test_keywords.resource",
                                      "reports/combined.k6-report.md",
                                      "resources/python/combined_tasks.py", "tests/combined.robot"]
    suite = combined.files["tests/combined.robot"]
    assert "Combined Load - Ramp To 20 Users - Thresholds Met\n" in suite
    assert suite.count("Resource") == 1
    assert suite.rstrip().endswith("    Test Combined Load")


def test_scenarios_become_weighted_classes(combined: emit.Conversion) -> None:
    keywords = _keywords(combined, "combined")
    assert "    Add User Class    signup    weight=8\n" in keywords
    assert "    Add Python Task    otpScenario    combined_tasks.otpScenario\n" in keywords
    assert "verify_tls=${False}" in keywords
    assert "    Set Load Stages    120s:20    600s:20    60s:0\n" in keywords


def test_thresholds_loop_over_listed_endpoints(combined: emit.Conversion) -> None:
    keywords = _keywords(combined, "combined")
    assert "@{COMBINED_CHECK_1_ENDPOINTS}    register    token\n...    verify-phone" in keywords
    assert "    FOR    ${endpoint}    IN    @{COMBINED_CHECK_1_ENDPOINTS}\n" in keywords
    assert "        Should Meet Response Time    ${endpoint}    p95    1000ms\n" in keywords
    assert "        Should Meet Error Rate    1%    endpoint=${endpoint}\n" in keywords


def test_flows_are_stubs_listed_in_the_report(combined: emit.Conversion) -> None:
    with pytest.raises(NotImplementedError, match="combined.js line 40"):
        _tasks(combined, "combined").signupScenario(object())
    report = combined.files["reports/combined.k6-report.md"]
    assert "| scenario signup | hand port | line 41: signupFlow()" in report


def _project(tmp_path: Path, done: emit.Conversion) -> Path:
    for relative, text in done.files.items():
        (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / relative).write_text(text, encoding="utf-8")
    resources = tmp_path / "resources"
    (resources / "resources.resource").write_text(
        emit.entry_point(["combined_test_keywords.resource"]), encoding="utf-8")
    (resources / "variables.resource").write_text(emit.VARIABLES, encoding="utf-8")
    (resources / "dev_variables.resource").write_text(
        emit.env_variables("dev", done.host), encoding="utf-8")
    return tmp_path


def test_project_passes_dryrun_and_robocop(combined: emit.Conversion, tmp_path: Path) -> None:
    project = _project(tmp_path, combined)
    out = io.StringIO()
    rc = robot.run(str(project / "tests"), dryrun=True, output=None, report=None, log=None,
                   stdout=out, stderr=out)
    assert rc == 0, out.getvalue()
    lint = subprocess.run([sys.executable, "-m", "robocop", "check", str(project)],
                          capture_output=True, text=True, check=False)
    assert "No issues found" in lint.stdout, lint.stdout


def test_plain_function_becomes_client_calls() -> None:
    calls = (HttpCall("GET", "https://h/", "home"),
             HttpCall("POST", "https://h/login", "login", {"u": "a", "ok": True},
                      {"Content-Type": "application/json"}),
             HttpCall("POST", "https://h/form", "", "a=1"))
    opts = options.K6Options((options.K6Scenario("default", "shared-iterations", vus=2,
                                                 iterations=10),), (), False, 0.0, 2)
    done = emit.convert("plain.js", opts, [ExecFunction("default", 3, calls, 1.5)])
    seen: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    class Client:
        def __getattr__(self, verb: str) -> Any:
            return lambda *a, **k: seen.append((verb, a, k))

    _tasks(done, "plain").default(types.SimpleNamespace(client=Client()))
    assert seen[0] == ("get", ("https://h/",), {"name": "home"})
    assert seen[1][2]["json"] == {"u": "a", "ok": True}
    assert seen[2][2] == {"data": "a=1", "name": "https://h/form"}
    keywords = _keywords(done, "plain")
    assert "    Set Wait Time    1.5s    1.5s\n" in keywords
    assert "users=2    spawn_rate=2    run_time=600s    iterations=10    max_users=100" in keywords
    assert "    Should Have No Failures\n" in keywords
    assert "Plain Load - 10 Iterations By 2 Users - Thresholds Met" in done.files["tests/plain.robot"]
    assert done.host == "https://h"


def test_arrival_rate_is_clamped_and_flagged() -> None:
    done = emit.convert("highrate.js", _opts("highrate"), FLOWS)
    report = done.files["reports/highrate.k6-report.md"]
    assert "Run Load Test    users=100    spawn_rate=100    run_time=600s" in _keywords(done, "highrate")
    assert "| users | clamped | 3300 users cut to max_users=100 |" in report
    assert "| executors | approximate |" in report
    assert "Highrate Load - 100 Users For 600s" in done.files["tests/highrate.robot"]


def test_stage_timings_that_differ_are_flagged() -> None:
    a = options.K6Scenario("a", "ramping-vus", "fa", (Stage(10, 5),))
    b = options.K6Scenario("b", "ramping-vus", "fb", (Stage(20, 5),))
    done = emit.convert("x.js", options.K6Options((a, b), (), False, 0.0, 10), [])
    report = done.files["reports/x.k6-report.md"]
    assert "    Set Load Stages    10s:10\n" in _keywords(done, "x")
    assert "stage timings differ" in report
    assert "| scenario a | hand port | exec function fa not found |" in report


def test_big_stages_scale_down_to_the_ceiling() -> None:
    a = options.K6Scenario("a", "ramping-vus", "fa", (Stage(10, 400), Stage(10, 0)))
    opts = options.K6Options((a,), (), False, 0.0, 400)
    assert "    Set Load Stages    10s:100    10s:0\n" in _keywords(emit.convert("x.js", opts, []), "x")
    raised = emit.convert("x.js", opts, [], max_users=400)
    assert "Run Load Test    max_users=400\n" in _keywords(raised, "x")
    assert "Ramp To 400 Users" in raised.files["tests/x.robot"]


def test_single_and_unsupported_thresholds() -> None:
    opts = options.K6Options((), (options.Threshold("http_req_duration", "", "avg", 300.0),
                                  options.Threshold("iterations", "", "rate", 1.0),
                                  options.Threshold("http_req_duration", "", "p99", 900.0),
                                  options.Threshold("http_req_failed", "", "rate", 0.02)),
                             False, 0.0, 0)
    done = emit.convert("x.js", opts, [])
    report, keywords = done.files["reports/x.k6-report.md"], _keywords(done, "x")
    assert "| threshold http_req_duration avg | unsupported |" in report
    assert "| threshold iterations rate | unsupported |" in report
    assert "    Should Meet Response Time    aggregated    p99    900ms\n" in keywords
    assert "    Should Meet Error Rate    2%\n" in keywords


def test_report_escapes_pipes() -> None:
    a = options.K6Scenario("a", "constant-vus", "fa", vus=1, duration_s=5)
    fn = ExecFunction("fa", 1, reason="line 2: a || b is not a call")
    done = emit.convert("x.js", options.K6Options((a,), (), False, 0.0, 1), [fn])
    assert "a // b is not a call" in done.files["reports/x.k6-report.md"]
    assert "1 User For 5s" in done.files["tests/x.robot"]
