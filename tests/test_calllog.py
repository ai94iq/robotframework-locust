"""The request log keeps a sample per name and the failures, with secrets masked."""

from types import SimpleNamespace
from typing import Any

from LocustLibrary.calllog import CallLog, mask_body, mask_headers


def _response(status: int = 201, body: Any = '{"password": "p", "user": "a"}',
              text: str = '{"access_token": "t", "id": 7}') -> Any:
    request = SimpleNamespace(method="POST", url="https://h/v1/x", path_url="/v1/x",
                              headers={"Authorization": "Bearer t", "Accept": "*/*"}, body=body)
    return SimpleNamespace(request=request, url="https://h/v1/x", status_code=status,
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
    log.record(request_type="POST", name="register", response_time=410.4, response=_response())
    block = log.entries[0]
    assert block.startswith("<details><summary>POST register 201 410 ms</summary><pre>")
    assert "POST Request : url=https://h/v1/x" in block
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
