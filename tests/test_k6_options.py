"""k6 inspect output becomes typed options the emitter can map."""

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from LocustLibrary.k6 import options
from LocustLibrary.scenario import Stage

FIXTURES = Path(__file__).parent / "fixtures" / "k6"


def _load(name: str) -> options.K6Options:
    data = json.loads((FIXTURES / f"{name}.inspect.json").read_text(encoding="utf-8"))
    return options.parse_options(data)


@pytest.mark.parametrize(("text", "seconds"), [
    ("2m0s", 120), ("1h2m3s", 3723), ("500ms", 0.5), ("1.5s", 1.5), ("10m", 600),
])
def test_go_durations(text: str, seconds: float) -> None:
    assert options.go_seconds(text) == pytest.approx(seconds)


@pytest.mark.parametrize("text", ["", "2x", "abc", "1m2"])
def test_bad_duration_is_rejected(text: str) -> None:
    with pytest.raises(ValueError, match="duration"):
        options.go_seconds(text)


def test_ramping_scenarios_keep_their_stages() -> None:
    opts = _load("combined")
    signup = next(s for s in opts.scenarios if s.name == "signup")
    assert [s.name for s in opts.scenarios] == ["otp", "signup", "token"]
    assert signup.executor == "ramping-vus"
    assert signup.exec_name == "signupScenario"
    assert signup.stages == (Stage(120, 8), Stage(600, 8), Stage(60, 0))
    assert (opts.insecure, opts.max_vus, opts.total_s) == (True, 20, pytest.approx(810))


def test_thresholds_carry_endpoint_and_limit() -> None:
    opts = _load("combined")
    found = {(t.metric, t.endpoint, t.stat, t.limit) for t in opts.thresholds}
    assert ("http_req_duration", "register", "p95", 1000.0) in found
    assert ("http_req_failed", "token", "rate", 0.01) in found
    assert len(found) == 6


def test_arrival_rate_reads_rate_per_second() -> None:
    signup = next(s for s in _load("highrate").scenarios if s.name == "signup")
    assert (signup.rate, signup.max_vus, signup.duration_s) == (200.0, 1200, 600.0)


def test_shared_iterations_default_scenario() -> None:
    (only,) = _load("stress_get").scenarios
    assert (only.name, only.exec_name, only.vus, only.iterations) == ("default", "default", 10, 5000)


@pytest.mark.parametrize(("metric", "expr", "parsed"), [
    ("http_req_duration", "p(99.9)<=250", ("http_req_duration", "", "p999", 250.0)),
    ("http_req_failed{endpoint:x}", "rate<0.05", ("http_req_failed", "x", "rate", 0.05)),
    ("http_req_duration{endpoint:a b}", "avg<300", ("http_req_duration", "a b", "avg", 300.0)),
])
def test_threshold_forms(metric: str, expr: str, parsed: tuple[Any, ...]) -> None:
    (one,) = options.parse_thresholds({metric: [expr]})
    assert (one.metric, one.endpoint, one.stat, one.limit) == parsed


def test_unknown_threshold_is_rejected() -> None:
    with pytest.raises(ValueError, match="threshold"):
        options.parse_thresholds({"http_req_duration": ["p95 under 1s"]})


def test_inspect_runs_k6_with_env_and_timeout(monkeypatch, tmp_path: Path) -> None:
    seen: dict[str, Any] = {}

    def run(args: list[str], **kwargs: Any) -> Any:
        seen.update(args=args, **kwargs)
        return subprocess.CompletedProcess(args, 0, stdout='{"vus": 1}', stderr="")

    monkeypatch.setattr(options.shutil, "which", lambda _name: "/bin/k6")
    monkeypatch.setattr(options.subprocess, "run", run)
    script = tmp_path / "a.js"
    assert options.run_inspect(script, {"HOLD": "1m"}) == {"vus": 1}
    assert seen["args"] == ["/bin/k6", "inspect", "--execution-requirements",
                            "-e", "HOLD=1m", str(script)]
    assert (seen["timeout"], seen["check"]) == (60, True)


def test_inspect_needs_k6(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(options.shutil, "which", lambda _name: None)
    with pytest.raises(FileNotFoundError, match="k6"):
        options.run_inspect(tmp_path / "a.js", {})
