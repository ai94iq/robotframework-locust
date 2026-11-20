"""Run Load Test shows its stats and calls in the Robot log; Export Report writes the files."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import LocustLibrary as lib_module
from LocustLibrary import LocustLibrary, runner
from LocustLibrary.calllog import CallLog
from LocustLibrary.reporting import stats_table_html
from LocustLibrary.scenario import Stats, StatsRow


def _stats() -> Stats:
    row = StatsRow(name="<i>login</i>", request_count=207, failure_count=1, median=680.0,
                   p95=1100.0, p99=1500.0, max=1575.6, rps=0.4393)
    return Stats(rows=[row], aggregated=StatsRow(name="Aggregated", request_count=207),
                 calls=["<details>one</details>"], left_out=4, report_html="<html>report</html>")


def _messages(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, bool]]:
    seen: list[tuple[str, str, bool]] = []
    fake = SimpleNamespace(
        info=lambda msg, html=False: seen.append(("INFO", msg, html)),
        warn=lambda msg, html=False: seen.append(("WARN", msg, html)))
    monkeypatch.setattr(lib_module, "logger", fake)
    return seen


def test_table_has_a_row_per_name() -> None:
    table = stats_table_html(_stats())
    assert "<td>&lt;i&gt;login&lt;/i&gt;</td><td>207</td><td>1</td><td>680</td><td>1100</td>" in table
    assert "<td>Aggregated</td>" in table and "<td>0.44</td>" in table


def test_run_logs_table_calls_and_tls(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _messages(monkeypatch)
    monkeypatch.setattr(lib_module, "run_load_test", lambda _s, _c: _stats())
    lib = LocustLibrary()
    lib.create_load_test("https://h.test", verify_tls=False)
    lib.run_load_test(users=1, run_time="1s")
    assert seen[0] == ("WARN", "TLS verification is off for https://h.test", False)
    assert seen[1][1].startswith("<table") and seen[1][2]
    assert seen[2] == ("INFO", "<details>one</details>", True)
    assert "4 more calls not logged" in seen[3][1]


def test_csv_prefix_is_gone() -> None:
    lib = LocustLibrary()
    lib.create_load_test("http://127.0.0.1")
    with pytest.raises(TypeError):
        lib.run_load_test(csv_prefix="x")  # type: ignore[call-arg]


def test_export_writes_csv_and_linked_html(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    seen = _messages(monkeypatch)
    monkeypatch.setattr(lib_module, "_output_dir", lambda: str(tmp_path))
    lib = LocustLibrary()
    lib._stats = _stats()
    base = lib.export_report("combined")
    assert Path(base) == tmp_path / "combined"
    assert (tmp_path / "combined_stats.csv").is_file()
    assert (tmp_path / "combined.html").read_text(encoding="utf-8") == "<html>report</html>"
    assert seen == [("INFO", 'Locust report: <a href="combined.html">combined.html</a>', True)]


def test_output_dir_outside_robot_is_cwd() -> None:
    assert lib_module._output_dir() is None


def test_observe_listens_on_request_events() -> None:
    added: list[Any] = []
    env = SimpleNamespace(events=SimpleNamespace(request=SimpleNamespace(add_listener=added.append)))
    calls = runner._observe(env)
    assert added == [calls.record]


def test_finish_adds_calls_and_report(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "_stats_from_env", lambda _env: Stats())
    monkeypatch.setattr(runner, "write_html_report", lambda _env: "<html>r</html>")
    calls = CallLog(entries=["a"], left_out=2)
    stats = runner._finish(object(), calls)
    assert (stats.calls, stats.left_out, stats.report_html) == (["a"], 2, "<html>r</html>")
