"""The request log keeps a sample per name and the failures, with secrets masked."""

import time
from types import SimpleNamespace
from typing import Any

from LocustLibrary.calllog import CallLog, mask_body, mask_headers, mask_url, masked_names


def _response(status: int = 201, body: Any = '{"password": "p", "user": "a"}',
              text: str = '{"access_token": "t", "id": 7}') -> Any:
    request = SimpleNamespace(method="POST", url="https://h/v1/x", path_url="/v1/x",
                              headers={"Authorization": "Bearer t", "Accept": "*/*"}, body=body)
    return SimpleNamespace(request=request, url="register", status_code=status,
                           reason="Created", headers={"Set-Cookie": "s=1"}, text=text)


def test_keeps_three_calls_per_name() -> None:
    log = CallLog()
    for _ in range(5):
        log.record(request_type="POST", name="register", response_time=12.0, response=_response())
    assert (len(log.entries), log.left_out) == (3, 2)


def test_keeps_failures_up_to_fifty() -> None:
    log = CallLog()
    for _ in range(60):
        log.record(request_type="POST", name="token", response_time=5.0, response=_response(500),
                   exception=RuntimeError("500 Server Error"))
    assert (len(log.entries), log.left_out) == (53, 7)


def test_block_reads_like_requests_library() -> None:
    log = CallLog()
    log.record(request_type="POST", name="register", response_time=410.4, response=_response(),
               start_time=0.0)
    block = log.entries[0]
    sent = time.strftime("%H:%M:%S", time.localtime(0.0))
    assert block.startswith(f"<details><summary>{sent} POST register 201 410 ms</summary><pre style=")
    assert "white-space:pre-wrap" in block
    assert "POST Request : url=https://h/v1/x" in block
    assert "POST Response : url=https://h/v1/x" in block
    assert "status=201, reason=Created" in block
    assert "Bearer" not in block
    assert "&quot;p&quot;" not in block and "&quot;t&quot;" not in block
    assert "&quot;password&quot;: &quot;***&quot;" in block


def test_failure_and_missing_response() -> None:
    log = CallLog()
    log.record(request_type="RF", name="<b>kw</b>", response_time=3.0, exception=ValueError("boom"))
    block = log.entries[0]
    assert "&lt;b&gt;kw&lt;/b&gt;" in block and "<b>" not in block
    assert "FAILED: boom" in block


def test_headers_and_form_bodies_are_masked() -> None:
    assert mask_headers({"Cookie": "a", "X": "b"}) == {"Cookie": "***", "X": "b"}
    form = mask_body(b"grant_type=password&client_secret=s&password=p%40ss")
    assert form == "grant_type=password&client_secret=***&password=***"


def test_nested_json_is_masked() -> None:
    assert mask_body('{"a": [{"otp": "1234"}], "b": 1}') == '{"a": [{"otp": "***"}], "b": 1}'


def test_plain_text_is_kept_and_cut() -> None:
    assert mask_body(None) == ""
    assert mask_body("<html>hi</html>") == "<html>hi</html>"
    assert mask_body("x" * 10005).endswith("... (cut at 10000 characters)")


def test_api_key_headers_are_masked_by_default() -> None:
    names = ["X-Api-Key", "Api-Key", "X-Auth-Token", "X-Access-Token"]
    assert mask_headers({n: "s" for n in names}) == {n: "***" for n in names}


def test_extra_masked_names_extend_headers_and_bodies() -> None:
    extra = masked_names(" X-Tenant-Secret , PIN,")
    assert mask_headers({"x-tenant-secret": "s"}, extra) == {"x-tenant-secret": "***"}
    assert mask_body('{"Pin": "1"}', extra) == '{"Pin": "***"}'
    assert mask_url("/p?pin=1", extra) == "/p?pin=***"
    calls = CallLog(masked=extra)
    calls.record("POST", "/x", 5, response=_response(body='{"pin": "9"}'))
    assert "&quot;pin&quot;: &quot;***&quot;" in calls.entries[0]


def test_query_values_of_masked_names_are_masked() -> None:
    assert mask_url("https://h/p?access_token=t&q=1") == "https://h/p?access_token=***&q=1"
    assert mask_url("/p?api-key=k") == "/p?api-key=***"
    assert mask_url("/p") == "/p"
    assert mask_url("/p?%%%=&&") == "/p?%%%=&&"


def test_a_bare_key_does_not_unmask_the_query() -> None:
    assert mask_url("/p?access_token=abc&debug") == "/p?access_token=***&debug"
    assert mask_url("https://h/p?debug&Password=x&q=1") == "https://h/p?debug&Password=***&q=1"


def test_failure_text_and_request_name_are_masked() -> None:
    calls = CallLog()
    calls.record("GET", "/p?access_token=abc", 5,
                 exception=ConnectionError("Max retries exceeded with url: /p?debug&access_token=abc"))
    assert "abc" not in calls.entries[0]
    assert "access_token=***" in calls.entries[0]


def test_library_mask_argument_stays_with_its_library() -> None:
    from LocustLibrary import LocustLibrary

    LocustLibrary(mask="X-Leak-Secret")
    assert mask_headers({"X-Leak-Secret": "s"}) == {"X-Leak-Secret": "s"}
    assert mask_body('{"x-leak-secret": "1"}') == '{"x-leak-secret": "1"}'


def test_library_mask_reaches_its_run_config(monkeypatch) -> None:
    import LocustLibrary as lib_module
    from LocustLibrary.scenario import Stats

    seen: list[frozenset[str]] = []
    monkeypatch.setattr(lib_module, "run_load_test", lambda _s, c: seen.append(c.mask) or Stats())
    lib = lib_module.LocustLibrary(mask="X-Own")
    lib.create_load_test("https://example.com")
    lib.run_load_test(users=1)
    assert seen == [frozenset({"x-own"})]
