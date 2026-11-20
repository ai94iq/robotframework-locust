"""Read a load suite's user classes and tasks for Studio.

A Robot dry run walks the suite, so classes built inside resource keywords are found the way
Robot resolves them. Library keywords do not run in a dry run, so nothing is sent.
"""

import io
from dataclasses import dataclass, field
from typing import Any

from robot.errors import VariableError
from robot.libraries.BuiltIn import BuiltIn
from robot.run import run

_TASKS = {"Add Python Task", "Add Get Request", "Add Post Request", "Add Task"}


@dataclass
class PlannedClass:
    name: str
    size: str = ""
    wait: str = ""
    pacing: str = ""
    tasks: list[str] = field(default_factory=list)


@dataclass
class SuitePlan:
    host: str = ""
    classes: list[PlannedClass] = field(default_factory=list)
    stop_rules: list[str] = field(default_factory=list)

    def add(self, keyword: str, args: tuple[str, ...]) -> None:
        if keyword == "Create Load Test":
            self.host = args[0] if args else ""
        elif keyword == "Add User Class":
            self.classes.append(PlannedClass(args[0], " ".join(args[1:])))
        elif keyword == "Set Wait Time":
            self._current().wait = " - ".join(args)
        elif keyword == "Set Pacing":
            self._current().pacing = args[0]
        elif keyword == "Add Stop Rule":
            self.stop_rules.append(args[0])
        elif keyword in _TASKS:
            self._current().tasks.append(f"{keyword}: {args[0]}")

    def _current(self) -> PlannedClass:
        if not self.classes:
            self.classes.append(PlannedClass("RFUser"))
        return self.classes[-1]


class _Collector:
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, plan: SuitePlan) -> None:
        self.plan = plan

    def start_library_keyword(self, _data: Any, implementation: Any, result: Any) -> None:
        if implementation.owner.name == "LocustLibrary":
            self.plan.add(result.name, tuple(_resolve(str(arg)) for arg in result.args))


def _resolve(arg: str) -> str:
    # A dry run passes arguments as written; values from resource files still sit in scope.
    try:
        return str(BuiltIn().replace_variables(arg))
    except VariableError:
        return arg


def read_suite(path: str) -> SuitePlan:
    plan = SuitePlan()
    run(path, dryrun=True, listener=_Collector(plan), output="NONE", log="NONE",
              report="NONE", stdout=io.StringIO(), stderr=io.StringIO())
    return plan
