"""Turn the Build tab's tasks into a Robot suite, so every Studio run goes through Robot."""

from pathlib import Path
from typing import Any

from robot.utils import escape

from LocustLibrary.k6.robot_files import FAIL_RATIO, STOP_RULES

SEP = "    "
SPLITS = ("  ", "\t", "\n", "\r")


def cell(value: object) -> str:
    """One positional Robot cell; refuses text that Robot would split or read as syntax."""
    text = str(value)
    if not text or text != text.strip() or any(mark in text for mark in SPLITS):
        raise ValueError(f"{text!r} cannot be one suite value: no empty value, edge spaces, "
                         "double spaces, tabs or line breaks")
    escaped = str(escape(text))
    return "\\" + escaped if escaped.startswith("#") else escaped


def _task(task: dict[str, Any]) -> str:
    keyword = "Add Get Request" if task["method"] == "GET" else "Add Post Request"
    return SEP.join([keyword, cell(task["name"]), cell(task["path"]), f"weight={int(task['weight'])}"])


def _steps(scenario: dict[str, Any], run: dict[str, Any]) -> list[str]:
    load = ["Run Load Test", f"users={int(run['users'])}", f"spawn_rate={float(run['spawn_rate'])}",
            f"run_time={cell(run['run_time'])}", f"stop_on_fail_ratio={FAIL_RATIO}"]
    return [SEP.join(["Create Load Test", cell(scenario["host"])]),
            SEP.join(["Set Wait Time", cell(scenario["wait_min"]), cell(scenario["wait_max"])]),
            *(_task(task) for task in scenario["tasks"]),
            *(f"Add Stop Rule{SEP}{rule}" for rule in STOP_RULES),
            SEP.join(load),
            "Export Report"]


def suite_text(scenario: dict[str, Any], run: dict[str, Any]) -> str:
    """The suite for the Build tab's host, wait time and tasks and the Run tab's load values."""
    return "\n".join(["*** Settings ***",
                      "Documentation       Load test built on the Studio Build tab.",
                      "Library             LocustLibrary", "", "",
                      "*** Test Cases ***",
                      "Built Load Test",
                      *(SEP + step for step in _steps(scenario, run))]) + "\n"


def write_suite(scenario: dict[str, Any], run: dict[str, Any], path: Path) -> Path:
    """Write the built suite to path and return it."""
    path.write_text(suite_text(scenario, run), encoding="utf-8")
    return path
