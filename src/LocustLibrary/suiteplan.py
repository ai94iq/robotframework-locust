"""Read a load suite's user classes and tasks for Studio.

The suite and its resource files are parsed, never run: no library or variable file is imported.
User keywords are followed to the LocustLibrary keywords they call, and arguments resolve from
*** Variables *** sections of the suite and its resource files and from the user keyword's own
[Arguments]. Each child suite of a directory is read with its own variables and keywords.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from robot.errors import DataError
from robot.running import ResourceFileBuilder, TestSuite, TestSuiteBuilder
from robot.variables import Variables

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


def _norm(name: str) -> str:
    return name.lower().replace(" ", "").replace("_", "")


_KEYWORDS = {_norm(k): k for k in
             {"Create Load Test", "Add User Class", "Set Wait Time", "Set Pacing", "Add Stop Rule", *_TASKS}}


class _Reader:
    def __init__(self, plan: SuitePlan) -> None:
        self.plan = plan
        self.variables = Variables()
        self.keywords: dict[str, Any] = {}
        self.seen: set[Path] = set()

    def load(self, resource: Any, source: Path) -> None:
        self.variables.set_from_variable_section(resource.variables)
        for keyword in resource.keywords:
            self.keywords.setdefault(_norm(keyword.name), keyword)
        for item in resource.imports:
            if item.type != "RESOURCE":
                continue
            path = (source.parent / self.resolve(item.name)).resolve()
            if path.is_file() and path not in self.seen:
                self.seen.add(path)
                self.load(ResourceFileBuilder().build(path), path)

    def resolve(self, arg: str) -> str:
        try:
            return str(self.variables.replace_string(arg))
        except DataError:
            return arg

    def walk(self, body: Any, stack: tuple[str, ...] = ()) -> None:
        for step in body:
            if step.type in ("KEYWORD", "SETUP", "TEARDOWN") and step.name:
                self.call(step.name, step.args, stack)
            if hasattr(step, "body"):
                self.walk(step.body, stack)

    def call(self, name: str, args: Any, stack: tuple[str, ...]) -> None:
        key = _norm(name.removeprefix("LocustLibrary."))
        if key in _KEYWORDS:
            self.plan.add(_KEYWORDS[key], tuple(self.resolve(str(arg)) for arg in args))
        elif key in self.keywords and key not in stack:
            keyword = self.keywords[key]
            values = [self.resolve(str(arg)) for arg in args]
            outer = self.variables
            self.variables = outer.copy()
            try:
                self._bind(keyword.args, values)
                self.walk([keyword.setup, *keyword.body, keyword.teardown], (*stack, key))
            finally:
                self.variables = outer

    def _bind(self, spec: Any, values: list[str]) -> None:
        names = list(spec.positional)
        bound = {name: self.resolve(str(value)) for name, value in spec.defaults.items()}
        free = iter(names)
        for value in values:
            name, sep, named = value.partition("=")
            if sep and name in names:
                bound[name] = named
            elif (slot := next(free, None)) is not None:
                bound[slot] = value
        for name, value in bound.items():
            self.variables[f"${{{name}}}"] = value

    def suite(self, suite: TestSuite) -> None:
        if suite.source and suite.resource:
            self.load(suite.resource, Path(suite.source))
        self.walk([suite.setup])
        for test in suite.tests:
            self.walk([test.setup, *test.body, test.teardown])
        self.walk([suite.teardown])
        for child in suite.suites:
            _Reader(self.plan).suite(child)


def read_suite(path: str) -> SuitePlan:
    plan = SuitePlan()
    _Reader(plan).suite(TestSuiteBuilder().build(path))
    return plan
