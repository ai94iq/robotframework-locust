"""The scanner finds exec functions and the plain HTTP calls inside them."""

import pytest

from LocustLibrary.k6 import scan

SIMPLE = """
import http from "k6/http";
import { check, sleep } from "k6";

export const options = { vus: 1 };

export default function () {
  const res = http.get("https://test.k6.io/", { tags: { endpoint: "home" } });
  check(res, { "ok": (r) => r.status === 200 });
  http.post("https://test.k6.io/login", JSON.stringify({ user: "a", n: 2, ok: true, x: null }),
    { headers: { "Content-Type": "application/json" }, tags: { endpoint: "login" } });
  sleep(1.5);
}

export function tokenScenario() {
  tokenFlow();
  sleep(1);
}
"""


@pytest.fixture(scope="module")
def found() -> dict[str, scan.ExecFunction]:
    return {f.name: f for f in scan.scan_source(SIMPLE)}


def test_default_function_is_simple(found: dict[str, scan.ExecFunction]) -> None:
    default = found["default"]
    assert default.simple
    assert default.think_s == 1.5
    assert default.line == 7


def test_calls_keep_method_url_tag_and_body(found: dict[str, scan.ExecFunction]) -> None:
    get, post = found["default"].calls
    assert (get.method, get.url, get.endpoint, get.body) == ("GET", "https://test.k6.io/", "home", None)
    assert (post.method, post.endpoint) == ("POST", "login")
    assert post.body == {"user": "a", "n": 2, "ok": True, "x": None}
    assert post.headers == {"Content-Type": "application/json"}


def test_helper_call_keeps_the_function_plain(found: dict[str, scan.ExecFunction]) -> None:
    token = found["tokenScenario"]
    assert token.simple
    assert token.helpers == (("tokenFlow", 16),)
    assert token.think_s == 1.0


@pytest.mark.parametrize(("body", "reason"), [
    ('http.get(`${BASE}/x`);', "URL is not a plain string"),
    ('http.post("https://h/x", JSON.stringify({ id: makeId() }));', "body is not a literal"),
    ('for (const x of y) { http.get("https://h/"); }', "for_in_statement"),
    ('http.post("https://h/x", "a=1");', ""),
])
def test_what_makes_a_function_need_a_hand_port(body: str, reason: str) -> None:
    (only,) = scan.scan_source(f"export default function () {{ {body} }}")
    assert only.simple is (reason == "")
    assert reason in only.reason


def test_helper_called_with_arguments_needs_hand_port() -> None:
    (only,) = scan.scan_source('export default function () { login("u"); }')
    assert not only.simple
    assert only.reason == "line 1: login() is not an HTTP call, check or sleep"
    assert only.helpers == ()


def test_array_body_and_shorthand_pair() -> None:
    (arr,) = scan.scan_source('export default function () { http.post("https://h/", JSON.stringify([1, "a"])); }')
    (short,) = scan.scan_source('export default function () { http.post("https://h/", JSON.stringify({ id })); }')
    assert arr.calls[0].body == [1, "a"]
    assert "body is not a literal" in short.reason


def test_raw_string_body_is_kept() -> None:
    (only,) = scan.scan_source('export default function () { http.post("https://h/x", "a=1"); }')
    assert only.calls[0].body == "a=1"


def test_non_exported_functions_are_ignored() -> None:
    assert scan.scan_source("function helper() { http.get('https://h/'); }") == []

NAMED_THINK = """
const THINK = Number(__ENV.THINK_SECONDS || 2);
const PAUSE = 0.5;

export function envThink() {
  http.get("https://h/");
  sleep(THINK);
}

export function plainThink() {
  sleep(PAUSE);
}

export function unknownThink() {
  sleep(later);
}
"""


@pytest.fixture(scope="module")
def named() -> dict[str, scan.ExecFunction]:
    return {f.name: f for f in scan.scan_source(NAMED_THINK)}


def test_think_from_env_default(named: dict[str, scan.ExecFunction]) -> None:
    assert named["envThink"].simple
    assert named["envThink"].think_s == 2.0


def test_think_from_number_constant(named: dict[str, scan.ExecFunction]) -> None:
    assert named["plainThink"].think_s == 0.5


def test_unknown_think_needs_hand_port(named: dict[str, scan.ExecFunction]) -> None:
    assert named["unknownThink"].reason == "line 15: later is not a literal"
