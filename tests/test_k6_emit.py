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
from locust.exception import StopUser

from LocustLibrary.k6 import emit, options, profile, robot_files, stubs
from LocustLibrary.k6.scan import ExecFunction, HttpCall, scan_source
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
    assert "Combined Load - Ramp To 20 Users - Mapped Thresholds Met\n" in suite
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
    assert "        Should Meet Response Time    ${endpoint}    p95    999ms\n" in keywords
    assert "        Should Meet Error Rate    1%    endpoint=${endpoint}\n" in keywords


def test_flows_are_stubs_listed_in_the_report(combined: emit.Conversion) -> None:
    fired: list[dict[str, Any]] = []
    user = types.SimpleNamespace(environment=types.SimpleNamespace(events=types.SimpleNamespace(
        request=types.SimpleNamespace(fire=lambda **kw: fired.append(kw)))))
    with pytest.raises(StopUser):
        _tasks(combined, "combined").signupScenario(user)
    assert [(f["request_type"], f["name"]) for f in fired] == [("HAND PORT", "signupScenario")]
    assert isinstance(fired[0]["exception"], NotImplementedError)
    assert "combined.js line 40" in str(fired[0]["exception"])
    report = combined.files["reports/combined.k6-report.md"]
    assert "| scenario signup | hand port | line 41: signupFlow()" in report


def test_run_refuses_to_start_while_stubs_remain(combined: emit.Conversion, monkeypatch) -> None:
    tasks = _tasks(combined, "combined")
    monkeypatch.setitem(sys.modules, "combined_tasks", tasks)
    assert tasks.signupScenario.__hand_port__ is True
    assert not hasattr(tasks, "check_hand_ports")
    with pytest.raises(AssertionError, match="otpScenario, signupScenario, tokenScenario"):
        stubs.check_hand_ports("combined_tasks", False)
    stubs.check_hand_ports("combined_tasks", True)
    run = _keywords(combined, "combined").split("\nRun Combined Load\n")[1].splitlines()
    assert run[1] == "    ${allow}=    Get Variable Value    ${ALLOW_STUBS}    ${False}"
    assert run[2] == ("    Evaluate    __import__('LocustLibrary.k6.stubs', fromlist=['_'])"
                      ".check_hand_ports('combined_tasks', $allow)")
    assert "${ALLOW_STUBS}      ${False}\n" in emit.env_variables("dev", "http://h")


def test_ported_tasks_pass_the_stub_check(monkeypatch) -> None:
    plain = ExecFunction("a", 1, calls=[HttpCall("GET", "http://h/x")])
    module = types.ModuleType("plain_tasks")
    source = robot_files.tasks_module("plain.js", [("a", plain)])
    exec(compile(source, "plain_tasks.py", "exec"), module.__dict__)  # noqa: S102
    monkeypatch.setitem(sys.modules, "plain_tasks", module)
    stubs.check_hand_ports("plain_tasks", False)


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
    assert "Plain Load - 10 Iterations By 2 Users - Mapped Thresholds Met" in done.files["tests/plain.robot"]
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
    assert "Run Load Test    max_users=400    stop_on_fail_ratio=20%\n    Export Report    x\n" in _keywords(raised, "x")
    assert "Ramp To 400 Users" in raised.files["tests/x.robot"]


def test_small_stage_after_scale_down_keeps_one_user() -> None:
    a = options.K6Scenario("a", "ramping-vus", "fa", (Stage(10, 1), Stage(10, 1000), Stage(10, 0)))
    opts = options.K6Options((a,), (), False, 0.0, 1000)
    assert "    Set Load Stages    10s:1    10s:100    10s:0\n" in _keywords(emit.convert("x.js", opts, []), "x")


def test_unparsed_threshold_is_an_unsupported_row() -> None:
    opts = options.parse_options({"thresholds": {"http_req_duration": ["p95 under 1s"]}})
    report = emit.convert("x.js", opts, []).files["reports/x.k6-report.md"]
    assert "| threshold http_req_duration | unsupported | cannot read p95 under 1s |" in report


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


def test_helper_call_keeps_http_calls_and_gets_a_report_row() -> None:
    opts = options.K6Options((options.K6Scenario("token", "constant-vus", "tokenScenario",
                                                 vus=1, duration_s=10),), (), False, 0.0, 1)
    fn = ExecFunction("tokenScenario", 3, (HttpCall("GET", "https://h/t", "t"),),
                      helpers=(("tokenFlow", 4),))
    done = emit.convert("helper.js", opts, [fn])
    tasks = done.files["resources/python/helper_tasks.py"]
    assert "user.client.get('https://h/t', name='t')" in tasks
    assert "NotImplementedError" not in tasks
    report = done.files["reports/helper.k6-report.md"]
    assert "| helper tokenFlow | hand port | helper.js line 4: tokenFlow() is not converted |" in report


def test_more_than_one_sleep_gets_an_approximate_row() -> None:
    (fn,) = scan_source("export function two() { sleep(1); http.get('https://h/a'); sleep(3); }")
    assert (fn.think_s, fn.sleeps) == (3.0, 2)
    opts = options.K6Options((options.K6Scenario("s", "constant-vus", "two",
                                                 vus=1, duration_s=10),), (), False, 0.0, 1)
    report = emit.convert("nap.js", opts, [fn]).files["reports/nap.k6-report.md"]
    assert "| sleep two | approximate | only the last sleep (3s) is used |" in report


def test_strict_threshold_emits_a_strict_check() -> None:
    raw = {"http_req_duration": ["p(95)<800", "p(99)<=900"], "http_req_failed": ["rate<0.01"]}
    report = profile.Report()
    lines, _ = profile.checks(options.parse_thresholds(raw), "S", report)
    assert "Should Meet Response Time    aggregated    p95    799ms" in lines
    assert "Should Meet Response Time    aggregated    p99    900ms" in lines
    assert ("threshold http_req_failed rate", "approximate",
            "k6 < is strict; the check also passes at exactly 1%") in report.rows


@pytest.mark.parametrize("executor", ["constant-vus", "shared-iterations"])
def test_plain_executors_get_a_mapped_row(executor: str) -> None:
    report = profile.Report()
    profile.load((options.K6Scenario("a", executor, vus=2, iterations=4, duration_s=5),), 10, report)
    assert report.rows[0][:2] == ("executors", "mapped")


def test_mixed_executors_drop_iteration_caps_get_an_approximate_row() -> None:
    report = profile.Report()
    lines, _ = profile.load((options.K6Scenario("a", "constant-vus", vus=2, duration_s=30),
                             options.K6Scenario("b", "shared-iterations", vus=1, iterations=7,
                                                duration_s=60)), 10, report)
    assert "iterations=" not in lines[0]
    assert report.rows[0] == ("executors", "approximate",
                              ("constant-vus, shared-iterations run as 3 users for 60s; "
                               "the iteration caps (7) are dropped, so the run ends on run_time alone"))


def _one(*urls: str) -> list[ExecFunction]:
    return [ExecFunction("default", 1, tuple(HttpCall("GET", u, "") for u in urls), 0.0)]


def _plain_opts() -> options.K6Options:
    return options.K6Options((options.K6Scenario("default", "shared-iterations", vus=1,
                                                 iterations=1),), (), False, 0.0, 1)


def test_host_is_the_most_common_origin_and_reported() -> None:
    done = emit.convert("multi.js", _plain_opts(),
                        _one("https://a/1", "https://b/1", "https://b/2", "https://a/2", "https://b/3"))
    assert done.host == "https://b"
    assert "| host | detected | https://b: most common origin, 3 of 5 calls |" in done.files[
        "reports/multi.k6-report.md"]


def test_host_tie_goes_to_the_first_origin_seen() -> None:
    done = emit.convert("tie.js", _plain_opts(), _one("https://a/1", "https://b/1", "https://b/2", "https://a/2"))
    assert done.host == "https://a"


def test_host_override_wins_and_is_reported() -> None:
    done = emit.convert("pick.js", _plain_opts(), _one("https://a/1"), host="http://other:8080")
    assert done.host == "http://other:8080"
    assert "| host | set by --host | http://other:8080 |" in done.files["reports/pick.k6-report.md"]


def test_host_override_must_be_plain() -> None:
    with pytest.raises(ValueError, match="host"):
        emit.convert("pick.js", _plain_opts(), [], host="http://${{1}}")


def test_suite_is_safe_by_default(combined: emit.Conversion) -> None:
    keywords = _keywords(combined, "combined")
    assert "allowed_hosts=${ALLOWED_HOSTS}" in keywords
    assert "    Add Stop Rule    fail > 10% for 30s\n" in keywords
    assert "    Add Stop Rule    idle > 30s\n" in keywords
    assert "    Run Load Test    " in keywords and "    stop_on_fail_ratio=20%\n" in keywords
    assert "${ALLOWED_HOSTS}      example.com\n" in emit.env_variables("dev", "https://example.com:8443")
    report = combined.files["reports/combined.k6-report.md"]
    assert "| safety | default | allowed_hosts" in report
    assert "fail > 10% for 30s" in report and "idle > 30s" in report and "stop_on_fail_ratio=20%" in report


def test_status_check_sets_expected_status_and_other_checks_get_a_row() -> None:
    src = """export default function () {
  const res = http.get('https://h/a', { tags: { endpoint: 'a' } });
  check(res, { 'is 201': (r) => r.status === 201, 'has id': (r) => r.json('id') !== '' });
}
"""
    fn = scan_source(src)[0]
    assert fn.calls[0].expected_status == 201
    assert fn.checks == (("has id", 3),)
    opts = options.K6Options((options.K6Scenario("s", "constant-vus", "default",
                                                 vus=1, duration_s=10),), (), False, 0.0, 1)
    done = emit.convert("chk.js", opts, [fn])
    tasks = done.files["resources/python/chk_tasks.py"]
    assert "catch_response=True) as response:" in tasks
    assert "response.failure(f'status {response.status_code} not 201')" in tasks
    report = done.files["reports/chk.k6-report.md"]
    assert "| check has id | unsupported | chk.js line 3: only r.status === N checks convert |" in report


def test_check_shapes_that_do_not_map_are_listed() -> None:
    src = """export default function () {
  check(null, { 'early': (r) => r.status === 200 });
  check(res);
  http.get('https://h/a');
  check(res, { 'body': (r) => { return true; }, 'size': (r) => r.body.length > 0 });
}
"""
    fn = scan_source(src)[0]
    assert fn.calls[0].expected_status is None
    assert fn.checks == (("early", 2), ("check", 3), ("body", 5), ("size", 5))
