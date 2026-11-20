"""HTTP tasks send headers and bodies and judge the status."""

from typing import Any, Self

import pytest

from LocustLibrary import LocustLibrary, runner
from LocustLibrary.scenario import Task


class _Response:
    def __init__(self, status: int) -> None:
        self.status_code = status
        self.verdict = ""

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def success(self) -> None:
        self.verdict = "ok"

    def failure(self, message: str) -> None:
        self.verdict = message


class _Client:
    def __init__(self, status: int) -> None:
        self.response = _Response(status)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def post(self, path: str, **kwargs: Any) -> _Response:
        self.calls.append((path, kwargs))
        return self.response


def _user(status: int) -> Any:
    class User:
        client = _Client(status)

    return User()


@pytest.mark.parametrize(("status", "verdict"), [(201, "ok"), (409, "ok"), (500, "status 500")])
def test_status_is_judged_against_accepted(status: int, verdict: str) -> None:
    user = _user(status)
    task = Task(name="create", method="POST", path="/x", expected=(201, 409))
    runner._run_http(user, task)
    assert user.client.response.verdict.startswith(verdict)


def test_headers_and_json_body_are_sent() -> None:
    user = _user(200)
    task = Task(name="save", method="POST", path="/x",
                headers={"Authorization": "Bearer t"}, json={"a": 1})
    runner._run_http(user, task)
    path, kwargs = user.client.calls[0]
    assert path == "/x"
    assert kwargs["headers"] == {"Authorization": "Bearer t"}
    assert kwargs["json"] == {"a": 1}
    assert kwargs["name"] == "save"
    assert kwargs["catch_response"] is True


@pytest.mark.parametrize(("value", "expected"), [
    (200, (200,)), ("200", (200,)), ("200, 204", (200, 204)), ([400, "401"], (400, 401)),
])
def test_keyword_reads_accepted_statuses(value: object, expected: tuple[int, ...]) -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    lib.add_post_request("save", "/x", expected_status=value, json={"a": 1},
                         headers={"X": "1"}, data="k=v")
    task = lib._scenario.tasks[0] if lib._scenario else None
    assert task is not None
    assert task.expected == expected
    assert (task.json, task.headers, task.body) == ({"a": 1}, {"X": "1"}, "k=v")


def test_blank_status_is_rejected() -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    with pytest.raises(ValueError, match="status"):
        lib.add_get_request("home", "/", expected_status=" ")
