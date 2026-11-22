"""Studio's Stop button ends a Build tab run cleanly."""

import os
import threading
from typing import Any

import pytest

from LocustLibrary import runner
from LocustLibrary.scenario import RunConfig
from LocustLibrary.studio import live
from LocustLibrary.users import Budget


def test_stop_event_ends_the_runner_wait_with_a_reason() -> None:
    stop = threading.Event()
    stop.set()
    reason = runner._wait_until(60, Budget(0), runner.stop_check(stop))
    assert reason == live.STOP_REASON == runner.STOP_REASON


def test_unset_or_missing_stop_event_never_stops() -> None:
    assert runner.stop_check(threading.Event())(0) == ""
    assert runner.stop_check(None)(0) == ""


def test_run_config_carries_the_stop_event() -> None:
    stop = threading.Event()
    assert RunConfig(stop_event=stop).stop_event is stop
    assert RunConfig().stop_event is None


KWARGS = {"host": "http://example.invalid", "wait_min": 0, "wait_max": 0, "tasks": [],
          "users": 1, "spawn_rate": 1, "run_time": "60s"}


class FakeWorker:
    def __init__(self, *_: Any) -> None:
        self.finished = self.error = self
        self.stop_calls = 0
        self.stopped = False

    def connect(self, _: Any) -> None: ...
    def start(self) -> None: ...

    def stop(self) -> None:
        self.stop_calls += 1
        self.stopped = True


def test_stop_button_works_for_build_tab_runs(monkeypatch: Any) -> None:
    pytest.importorskip("PySide6", reason="PySide6 not installed: Studio Stop button wiring is untested")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from LocustLibrary.studio import run_tab

    QApplication.instance() or QApplication([])
    monkeypatch.setattr(run_tab, "RunWorker", FakeWorker)
    tab = run_tab.RunTab(lambda: {**KWARGS, "tasks": [{"name": "a"}]})
    tab.run()
    assert tab.stop_btn.isEnabled()
    tab.stop_btn.click()
    assert tab._worker.stop_calls == 1
    tab._on_finished({"rows": [], "aggregated": {}})
    assert tab.status_label.text() == "Run stopped"
    assert not tab.stop_btn.isEnabled()
