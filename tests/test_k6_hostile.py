"""A k6 script from someone else must not put code into the generated files."""

import types

import pytest
from locust.exception import StopUser

from LocustLibrary.k6 import emit, options
from LocustLibrary.k6.scan import ExecFunction, HttpCall

_INLINE = "http://${{__import__('os').system('calc')}}"


def _convert_with_url(url: str) -> emit.Conversion:
    scenario = options.K6Scenario("a", "constant-vus", "fa", vus=1, duration_s=5)
    fn = ExecFunction("fa", 1, calls=[HttpCall("GET", url)])
    return emit.convert("x.js", options.K6Options((scenario,), (), False, 0.0, 1), [fn])


def test_plain_host_is_kept() -> None:
    assert _convert_with_url("https://api.example.test:8443/users").host == (
        "https://api.example.test:8443")


def test_robot_syntax_host_is_refused() -> None:
    done = _convert_with_url(_INLINE)
    assert done.host == "http://127.0.0.1"
    assert "| host | set by hand |" in done.files["reports/x.k6-report.md"]


@pytest.mark.parametrize("exec_name", ["x(user):\n    import os\ndef y", "a b", "1st"])
def test_unsafe_exec_name_is_refused(exec_name: str) -> None:
    with pytest.raises(ValueError, match="exec"):
        options.parse_options({"scenarios": {"a": {"executor": "constant-vus", "exec": exec_name}}})


@pytest.mark.parametrize("name", ["a\n    Evaluate    1", "a    b", "${x}"])
def test_unsafe_scenario_name_is_refused(name: str) -> None:
    with pytest.raises(ValueError, match="scenario"):
        options.parse_options({"scenarios": {name: {"executor": "constant-vus"}}})


@pytest.mark.parametrize("tag", ["a\n    Evaluate    1", "a    b", "${x"])
def test_unsafe_threshold_tag_is_refused(tag: str) -> None:
    with pytest.raises(ValueError, match="threshold"):
        options.parse_thresholds({f"http_req_duration{{endpoint:{tag}}}": ["p(95)<500"]})


def test_safe_names_still_parse() -> None:
    data = {"scenarios": {"sign-up_1": {"executor": "constant-vus", "exec": "signupScenario"}},
            "thresholds": {"http_req_duration{endpoint:verify-phone}": ["p(95)<500"]}}
    opts = options.parse_options(data)
    assert (opts.scenarios[0].name, opts.thresholds[0].endpoint) == ("sign-up_1", "verify-phone")


def test_hand_port_reason_stays_text() -> None:
    scenario = options.K6Scenario("a", "constant-vus", "fa", vus=1, duration_s=5)
    fn = ExecFunction("fa", 1, reason='"""; raise SystemExit("broke") #')
    done = emit.convert("x.js", options.K6Options((scenario,), (), False, 0.0, 1), [fn])
    module: dict[str, object] = {}
    exec(compile(done.files["resources/python/x_tasks.py"], "x_tasks.py", "exec"), module)  # noqa: S102
    fired: list[dict[str, object]] = []
    user = types.SimpleNamespace(environment=types.SimpleNamespace(events=types.SimpleNamespace(
        request=types.SimpleNamespace(fire=lambda **kw: fired.append(kw)))))
    with pytest.raises(StopUser):
        module["fa"](user)  # type: ignore[operator]
    assert isinstance(fired[0]["exception"], NotImplementedError)


def test_script_name_stays_text() -> None:
    with pytest.raises(ValueError, match="script name"):
        emit.convert('x"""; raise SystemExit("broke") #.js', options.K6Options((), (), False, 0.0, 1), [])


def test_variables_file_escapes_robot_syntax() -> None:
    text = emit.env_variables("${{1}}", _INLINE)
    assert "${HOST}             http://\\${{__import__" in text
    assert "Values for the \\${{1}} environment" in text
