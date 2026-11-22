"""Studio's Run, Stop and Save as suite buttons drive Build tab tasks through a Robot suite."""

import os
from pathlib import Path
from typing import Any

import pytest

SCENARIO = {"host": "http://127.0.0.1:8765", "wait_min": "0s", "wait_max": "0s",
            "tasks": [{"name": "Get Home", "method": "GET", "path": "/", "weight": 1}]}


class FakeProcess:
    def __init__(self) -> None:
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True


class FakeRun:
    def __init__(self, suite: str) -> None:
        self.suite = Path(suite)
        self.outdir = self.suite.parent
        self.process = FakeProcess()


def _run_tab(monkeypatch: Any) -> Any:
    pytest.importorskip("PySide6", reason="PySide6 not installed: Studio Run and Stop wiring is untested")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from LocustLibrary.studio import run_tab

    QApplication.instance() or QApplication([])
    monkeypatch.setattr(run_tab, "start_suite", FakeRun)
    return run_tab.RunTab(lambda: SCENARIO)


def test_build_tab_run_uses_a_suite(monkeypatch: Any) -> None:
    """With no suite open, Run writes the Build tab tasks to a suite and starts Robot on it."""
    tab = _run_tab(monkeypatch)
    tab.run()
    text = tab._suite_run.suite.read_text(encoding="utf-8")
    assert "Add Get Request    Get Home    /    weight=1" in text, text
    assert "users=10" in text, text


def test_stop_ends_a_build_tab_run(monkeypatch: Any) -> None:
    """Stop ends the Robot process of a Build tab run, as it does for an opened suite."""
    tab = _run_tab(monkeypatch)
    tab.run()
    assert tab.stop_btn.isEnabled(), "Stop is enabled while the run goes"
    tab.stop_btn.click()
    assert tab._suite_run.process.terminated, "Stop ended the Robot process"


def test_save_writes_the_built_suite(monkeypatch: Any, tmp_path: Path) -> None:
    """Save as suite writes the Build tab tasks to the file the user picks."""
    _run_tab(monkeypatch)
    from LocustLibrary.studio import app

    target = tmp_path / "saved.robot"
    monkeypatch.setattr(app.QFileDialog, "getSaveFileName", lambda *_: (str(target), ""))
    window = app.MainWindow()
    window.build_tab.tasks.append(SCENARIO["tasks"][0])
    window.build_tab.save_requested.emit()
    assert "Add Get Request    Get Home    /    weight=1" in target.read_text(encoding="utf-8")
