"""Round 4 review fixes: stop rule units, k6 check scanning, kept tasks, distributed start."""

import os
from pathlib import Path
from typing import Any

import pytest

from LocustLibrary import LocustLibrary, shared
from LocustLibrary.k6 import cli, robot_files, scan
from LocustLibrary.stoprules import parse_rule


def test_idle_rule_without_a_unit_is_refused() -> None:
    with pytest.raises(ValueError, match="idle needs a unit"):
        parse_rule("idle > 30")


@pytest.mark.parametrize(("text", "limit"), [("idle > 30ms", 30.0), ("idle > 30s", 30000.0)])
def test_idle_rule_with_a_unit_is_read(text: str, limit: float) -> None:
    assert parse_rule(text).limit == limit


def _one(body: str) -> scan.ExecFunction:
    (only,) = scan.scan_source(f'export default function () {{ {body} }}')
    return only


GET = 'const r = http.get("https://h/x");'


@pytest.mark.parametrize("number", ["200.0", "0xC8", "2e2", "0o310", "2_00"])
def test_any_js_spelling_of_a_whole_status_is_read(number: str) -> None:
    fn = _one(f'{GET} check(r, {{ ok: (r) => r.status === {number} }});')
    assert fn.calls[0].expected_status == 200
    assert fn.checks == ()


@pytest.mark.parametrize("number", ["200.5", "200n"])
def test_a_status_that_is_not_a_whole_number_is_an_unsupported_check(number: str) -> None:
    fn = _one(f'{GET} check(r, {{ ok: (r) => r.status === {number} }});')
    assert fn.calls[0].expected_status is None
    assert [name for name, _ in fn.checks] == ["ok"]


def test_status_of_another_object_is_not_the_response_status() -> None:
    fn = _one(f'{GET} check(r, {{ job: (res) => job.status === 200 }});')
    assert fn.calls[0].expected_status is None
    assert [name for name, _ in fn.checks] == ["job"]


def test_status_of_the_callback_parameter_is_read() -> None:
    fn = _one(f'{GET} check(r, {{ ok: res => res.status == 201 }});')
    assert fn.calls[0].expected_status == 201


def test_a_second_status_check_on_one_call_is_reported_not_overwritten() -> None:
    fn = _one(f'{GET} check(r, {{ a: (r) => r.status === 200 }}); check(r, {{ b: (r) => r.status === 201 }});')
    assert fn.calls[0].expected_status == 200
    assert [name for name, _ in fn.checks] == ["b"]


def test_a_check_after_a_helper_does_not_attach_to_the_earlier_call() -> None:
    fn = _one(f'{GET} helper(); check(r, {{ ok: (r) => r.status === 200 }});')
    assert fn.calls[0].expected_status is None
    assert [name for name, _ in fn.checks] == ["ok"]


def test_spread_and_shorthand_checks_keep_a_name() -> None:
    fn = _one(f'{GET} check(r, {{ ...more, quick }});')
    assert [name for name, _ in fn.checks] == ["...more", "quick"]


def test_a_body_number_python_cannot_read_needs_a_hand_port() -> None:
    fn = _one('http.post("https://h/", JSON.stringify({ n: 1n }));')
    assert "body is not a literal" in fn.reason


def test_fail_ratio_is_not_added_twice() -> None:
    line = f"Run Load Test{robot_files.SEP}stop_on_fail_ratio=5%"
    assert robot_files._fail_ratio(line) == line


def test_kept_tasks_file_missing_functions_is_reported(monkeypatch, tmp_path: Path) -> None:
    from tests.test_k6_cli import SCRIPT, _inspect

    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "robot"
    tasks = out / "resources/python/smoke_tasks.py"
    tasks.parent.mkdir(parents=True)
    tasks.write_text("def other(user):\n    pass\n", encoding="utf-8")
    cli.main([str(script), "--trust-script", "--out", str(out)])
    report = (out / "reports/smoke.k6-report.md").read_text(encoding="utf-8")
    assert "| tasks file | missing | default |" in report


def test_kept_tasks_file_that_does_not_parse_is_reported(monkeypatch, tmp_path: Path) -> None:
    from tests.test_k6_cli import SCRIPT, _inspect

    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "robot"
    tasks = out / "resources/python/smoke_tasks.py"
    tasks.parent.mkdir(parents=True)
    tasks.write_text("def (:\n", encoding="utf-8")
    cli.main([str(script), "--trust-script", "--out", str(out)])
    report = (out / "reports/smoke.k6-report.md").read_text(encoding="utf-8")
    assert "| tasks file | missing | default |" in report


def test_distributed_users_start_without_the_web_form(tmp_path, monkeypatch) -> None:
    from LocustLibrary import distributed

    seen: list[list[str]] = []

    class _Proc:
        def poll(self) -> int:
            return 0

    monkeypatch.setattr(distributed.subprocess, "Popen", lambda argv, **_: seen.append(argv) or _Proc())
    locustfile = tmp_path / "locustfile.py"
    locustfile.write_text("x = 1\n", encoding="utf-8")
    LocustLibrary().run_distributed(str(locustfile), processes=1, users=5)
    assert seen[0][-3:] == ["--users", "5", "--autostart"]
    LocustLibrary().run_distributed(str(locustfile), processes=1)
    assert "--autostart" not in seen[2]


def test_shared_queue_is_built_once_per_name(monkeypatch) -> None:
    built: list[int] = []
    real = shared.Queue
    monkeypatch.setattr(shared, "Queue", lambda **kw: built.append(1) or real(**kw))
    lib = LocustLibrary()
    lib.put_shared_value("id", 1)
    lib.put_shared_value("id", 2)
    assert lib.take_shared_value("id") == 1
    assert built == [1]


def test_studio_worker_says_when_stop_cannot_reach_the_run(monkeypatch) -> None:
    pytest.importorskip("PySide6", reason="PySide6 not installed: Studio worker Stop wiring is untested")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import LocustLibrary as package
    from LocustLibrary.studio import worker

    ran: list[Any] = []

    class _NoConfig:
        _config = None

        def create_load_test(self, _host: str) -> None: ...
        def set_wait_time(self, *_: Any) -> None: ...
        def run_load_test(self, **kw: Any) -> None:
            ran.append(kw)

    monkeypatch.setattr(package, "LocustLibrary", _NoConfig)
    errors: list[str] = []
    job = worker.RunWorker({"host": "http://h", "wait_min": 0, "wait_max": 0, "tasks": [],
                            "users": 1, "spawn_rate": 1, "run_time": "1s"}, "feed.jsonl")
    job.error.connect(errors.append)
    job.run()
    assert ran == []
    assert errors and "Stop" in errors[0]
