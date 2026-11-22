"""Runs the Build tab's tasks in process, so Studio can watch a run without a suite file."""

import os
import threading
from typing import Any

from PySide6.QtCore import QThread, Signal

from LocustLibrary import feed


class RunWorker(QThread):  # type: ignore[misc, unused-ignore]
    """Runs tasks built on the Build tab in process; the feed file carries the live charts."""

    finished = Signal(object)
    error = Signal(str)

    def __init__(self, scenario_kwargs: dict[str, Any], feed_path: str) -> None:
        super().__init__()
        self.kwargs = scenario_kwargs
        self.feed_path = feed_path
        self._stop = threading.Event()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def stop(self) -> None:
        """Ends the run at its next check; the stats so far still come back."""
        self._stop.set()

    def run(self) -> None:
        os.environ[feed.ENV] = self.feed_path
        try:
            from LocustLibrary import LocustLibrary

            lib = LocustLibrary()
            lib.create_load_test(self.kwargs["host"])
            lib.set_wait_time(self.kwargs["wait_min"], self.kwargs["wait_max"])
            for t in self.kwargs["tasks"]:
                add = lib.add_get_request if t["method"] == "GET" else lib.add_post_request
                add(t["name"], t["path"], weight=t["weight"])
            if lib._config is None:
                raise RuntimeError("Create Load Test made no run config, so Stop cannot reach "
                                   "this run; not started")
            lib._config.stop_event = self._stop
            lib.run_load_test(users=self.kwargs["users"], spawn_rate=self.kwargs["spawn_rate"],
                              run_time=self.kwargs["run_time"])
            self.finished.emit(lib.get_locust_stats())
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
        finally:
            os.environ.pop(feed.ENV, None)
