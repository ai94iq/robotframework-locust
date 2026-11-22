"""Literal options are read from the script itself; computed ones still need k6 inspect."""

from pathlib import Path
from typing import Any

import pytest

from LocustLibrary.k6 import cli
from LocustLibrary.k6.options import parse_options
from LocustLibrary.k6.scan import static_options

STATIC = """import http from 'k6/http';
export const options = {
  scenarios: {
    load: { executor: 'ramping-vus', exec: 'browse', startTime: '10s',
            stages: [{ duration: '1m', target: 5 }, { duration: '30s', target: 0 }] },
    // runs once
    once: { executor: 'shared-iterations', vus: 2, iterations: 4, duration: '1m30s' },
  },
  thresholds: { http_req_duration: ['p(95)<500'] },
};
export function browse() { http.get("https://h/x", { tags: { endpoint: "x" } }); }
"""


def _no_inspect(path: Path, env: dict[str, str]) -> dict[str, Any]:
    raise AssertionError("k6 inspect must not run for literal options")


def test_literal_options_need_no_inspect_and_no_trust(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "shop.js"
    script.write_text(STATIC, encoding="utf-8")
    monkeypatch.setattr(cli, "run_inspect", _no_inspect)
    out = tmp_path / "robot"
    assert cli.main([str(script), "--out", str(out)]) == 0
    report = (out / "reports" / "shop.k6-report.md").read_text(encoding="utf-8")
    assert "| options | read statically |" in report


def test_static_options_parse_like_inspect() -> None:
    opts = parse_options(static_options(STATIC))
    load, once = opts.scenarios
    assert (load.name, load.executor, load.exec_name, [s.users for s in load.stages]) == (
        "load", "ramping-vus", "browse", [5, 0])
    assert (once.vus, once.iterations, once.duration_s) == (2, 4, 90.0)
    assert opts.thresholds[0].stat == "p95"


COMPUTED = STATIC.replace("vus: 2", "vus: Number(__ENV.VUS)")


def test_computed_option_without_trust_names_the_option(tmp_path: Path) -> None:
    script = tmp_path / "shop.js"
    script.write_text(COMPUTED, encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        cli.main([str(script), "--out", str(tmp_path / "robot")])
    err = str(stop.value.code)
    assert "scenarios.once.vus" in err and "--trust-script" in err and "\n" not in err


def test_computed_option_with_trust_uses_inspect(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "shop.js"
    script.write_text(COMPUTED, encoding="utf-8")
    monkeypatch.setattr(cli, "run_inspect", lambda path, env: static_options(STATIC))
    out = tmp_path / "robot"
    assert cli.main([str(script), "--trust-script", "--out", str(out)]) == 0
    report = (out / "reports" / "shop.k6-report.md").read_text(encoding="utf-8")
    assert "| options | from k6 inspect | options.scenarios.once.vus is not a literal |" in report


@pytest.mark.parametrize(("body", "scenario"), [
    ("{ stages: [{ duration: '10s', target: 3 }] }",
     {"executor": "ramping-vus", "startVUs": 1, "stages": [{"duration": "10s", "target": 3}]}),
    ("{ vus: 2, stages: [{ duration: '10s', target: 3 }] }",
     {"executor": "ramping-vus", "startVUs": 2, "stages": [{"duration": "10s", "target": 3}]}),
    ("{ vus: 2, iterations: 6 }", {"executor": "shared-iterations", "vus": 2, "iterations": 6}),
    ("{ iterations: 6, duration: '1m' }",
     {"executor": "shared-iterations", "vus": 1, "iterations": 6, "maxDuration": "1m"}),
    ("{ vus: 3, duration: '20s' }", {"executor": "constant-vus", "vus": 3, "duration": "20s"}),
    ("{ vus: 2 }", {"executor": "shared-iterations", "vus": 2, "iterations": 2}),
    ("{ vus: 2, scenarios: { a: { executor: 'constant-vus', vus: 9, duration: '1s' } } }",
     {"executor": "shared-iterations", "vus": 2, "iterations": 2}),
    ("{ vus: 2, stages: [] }", {"executor": "shared-iterations", "vus": 1, "iterations": 1}),
    ("{ thresholds: {} }", {"executor": "shared-iterations", "vus": 1, "iterations": 1}),
])
def test_top_level_shortcuts_become_the_default_scenario(body: str, scenario: dict[str, Any]) -> None:
    data = static_options(f"export const options = {body};")
    assert data["scenarios"] == {"default": scenario}


@pytest.mark.parametrize("body", [
    "{ iterations: 1, stages: [{ duration: '1s', target: 1 }] }",
    "{ duration: '1s', stages: [{ duration: '1s', target: 1 }] }",
    "{ iterations: 1, scenarios: {} }",
    "{ duration: '1s', scenarios: {} }",
    "{ stages: [{ duration: '1s', target: 1 }], scenarios: {} }",
])
def test_shortcuts_k6_refuses_together_are_refused(body: str) -> None:
    with pytest.raises(ValueError, match="simultaneously is not allowed"):
        static_options(f"export const options = {body};")


@pytest.mark.parametrize(("source", "why"), [
    ("export default function () {}", "no export const options"),
    ("export const other = 1;", "no export const options"),
    ("export let options;", "options is not a literal object"),
    ("export const options = { a: [1, /* c */ x] };", "options.a[1] is not a literal"),
    ("const options = { vus: 1 }; export { options };", "no export const options"),
    ("export const options = makeOptions();", "options is not a literal object"),
    ("export const options = { ...base };", "options has a key that is not a plain name"),
    ("export const options = { [k]: 1 };", "options has a key that is not a plain name"),
    ("export const options = { vus: -1 };", "options.vus is not a literal"),
    ("export const options = { s: `a${b}` };", "options.s is not a literal"),
    ("export const options = { t: { 'p': [x] } };", "options.t.p[0] is not a literal"),
])
def test_non_static_options_say_why(source: str, why: str) -> None:
    with pytest.raises(ValueError, match=__import__("re").escape(why)):
        static_options(source)
