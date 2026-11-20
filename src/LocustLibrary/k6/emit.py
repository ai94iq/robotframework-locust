"""Turn k6 options and scanned functions into a Robot project, following the four-layer
house layout: a thin suite in tests/, its steps in collections/, one entry resource, the
Python tasks under resources/python/, and a report of what needs a hand port.
"""

import re
from dataclasses import dataclass, field
from pathlib import PurePath
from urllib.parse import urlsplit

from .options import K6Options, K6Scenario, Threshold
from .scan import ExecFunction, HttpCall

_SEP = "    "
_PERCENTILES = {"p50", "p90", "p95", "p99", "p999"}
_DEFAULT_HOST = "http://127.0.0.1"
# HOST is written unquoted into a Robot Variables table, where ${{...}} would run as Python.
# The script name becomes file names, Robot cells and tags.
_SCRIPT_NAME = re.compile(r"[A-Za-z0-9_.-]+", re.ASCII)
_PLAIN_HOST = re.compile(r"https?://[A-Za-z0-9.-]+(:\d{1,5})?", re.ASCII)


@dataclass(frozen=True, slots=True)
class Conversion:
    """Files to write, keyed by their path under the output folder."""

    files: dict[str, str]
    host: str


@dataclass
class _Report:
    rows: list[tuple[str, str, str]] = field(default_factory=list)

    def add(self, item: str, status: str, note: str) -> None:
        self.rows.append((item, status, note.replace("|", "/")))

    def markdown(self, script: str) -> str:
        lines = [f"# k6 conversion report: {script}", "", "| Item | Status | Note |", "|---|---|---|"]
        return "\n".join([*lines, *(f"| {a} | {b} | {c} |" for a, b, c in self.rows)]) + "\n"


@dataclass(frozen=True, slots=True)
class _Steps:
    classes: list[str]
    load: list[str]
    checks: list[str]
    condition: str
    lists: dict[str, list[str]]


def convert(script: str, opts: K6Options, functions: list[ExecFunction],
            max_users: int = 100) -> Conversion:
    """Map what k6 and LocustLibrary share; list the rest as hand port or unsupported."""
    if not _SCRIPT_NAME.fullmatch(PurePath(script).name):
        raise ValueError(f"unsupported script name {script!r}")
    report = _Report()
    stem = PurePath(script).stem
    by_name = {f.name: f for f in functions}
    load, condition = _load(opts.scenarios, max_users, report)
    checks, lists = _checks(opts.thresholds, stem.upper(), report)
    steps = _Steps(_classes(opts.scenarios, by_name, f"{stem}_tasks", report), load,
                   checks, condition, lists)
    host = _host(functions, report)
    names = list(dict.fromkeys(s.exec_name for s in opts.scenarios))
    files = {
        f"tests/{stem}.robot": _suite(script, steps.condition),
        f"collections/{stem}_test_keywords.resource": _keywords(script, opts.insecure, steps),
        f"resources/python/{stem}_tasks.py": _tasks_module(script, [(n, by_name.get(n)) for n in names]),
        f"reports/{stem}.k6-report.md": report.markdown(script),
    }
    return Conversion(files, host)


def _title(script: str) -> str:
    return " ".join(PurePath(script).stem.replace("_", " ").split()).title()


def _peak(scenario: K6Scenario) -> int:
    if scenario.stages:
        return max(stage.users for stage in scenario.stages)
    return scenario.vus or scenario.max_vus


def _classes(scenarios: tuple[K6Scenario, ...], by_name: dict[str, ExecFunction],
             module: str, report: _Report) -> list[str]:
    lines: list[str] = []
    for s in scenarios:
        fn = by_name.get(s.exec_name)
        think = f"{fn.think_s if fn else 0:g}s"
        lines += [f"Add User Class{_SEP}{s.name}{_SEP}weight={max(1, _peak(s))}",
                  f"Set Wait Time{_SEP}{think}{_SEP}{think}",
                  f"Add Python Task{_SEP}{s.exec_name}{_SEP}{module}.{s.exec_name}"]
        if fn is None:
            report.add(f"scenario {s.name}", "hand port", f"exec function {s.exec_name} not found")
        elif fn.simple:
            report.add(f"scenario {s.name}", "mapped", f"{len(fn.calls)} HTTP calls")
        else:
            report.add(f"scenario {s.name}", "hand port", fn.reason)
    return lines


def _load(scenarios: tuple[K6Scenario, ...], max_users: int,
          report: _Report) -> tuple[list[str], str]:
    kinds = {s.executor for s in scenarios}
    if kinds == {"ramping-vus"}:
        return _staged(scenarios, max_users, report)
    users = sum(_peak(s) for s in scenarios)
    seconds = max((s.duration_s for s in scenarios), default=0.0) or 600.0
    iterations = sum(s.iterations for s in scenarios) if kinds <= {"shared-iterations"} else 0
    if not kinds <= {"shared-iterations", "constant-vus"}:
        report.add("executors", "approximate",
                   f"{', '.join(sorted(kinds))} run as {users} looping users; Locust has no arrival rate")
    if users > max_users:
        report.add("users", "clamped", f"{users} users cut to max_users={max_users}")
        users = max_users
    args = [f"users={users}", f"spawn_rate={users}", f"run_time={seconds:g}s"]
    args += [f"iterations={iterations}"] if iterations else []
    condition = (f"{_count(iterations, 'Iteration')} By {_count(users, 'User')}" if iterations
                 else f"{_count(users, 'User')} For {seconds:g}s")
    return [_SEP.join(["Run Load Test", *args, f"max_users={max_users}"])], condition


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def _staged(scenarios: tuple[K6Scenario, ...], max_users: int,
            report: _Report) -> tuple[list[str], str]:
    first = scenarios[0].stages
    timings = [st.seconds for st in first]
    if any([st.seconds for st in s.stages] != timings for s in scenarios):
        report.add("stages", "approximate", "stage timings differ; the first scenario's are used")
    totals = [sum(s.stages[i].users for s in scenarios if i < len(s.stages))
              for i in range(len(first))]
    peak = max(totals, default=0)
    scale = min(1.0, max_users / peak) if peak else 1.0
    if scale < 1.0:
        report.add("users", "clamped", f"{peak} users cut to max_users={max_users}")
    scaled = [round(t * scale) for t in totals]
    stages = _SEP.join(f"{st.seconds:g}s:{t}" for st, t in zip(first, scaled, strict=True))
    lines = [f"Set Load Stages{_SEP}{stages}", f"Run Load Test{_SEP}max_users={max_users}"]
    return lines, f"Ramp To {_count(max(scaled, default=0), 'User')}"


def _checks(thresholds: tuple[Threshold, ...], prefix: str,
            report: _Report) -> tuple[list[str], dict[str, list[str]]]:
    groups: dict[tuple[str, ...], list[str]] = {}
    for t in thresholds:
        item = f"threshold {t.metric} {t.stat}"
        if t.metric == "http_req_duration" and t.stat in _PERCENTILES:
            key: tuple[str, ...] = ("Should Meet Response Time", "${endpoint}", t.stat, f"{t.limit:g}ms")
        elif t.metric == "http_req_failed" and t.stat == "rate":
            key = ("Should Meet Error Rate", f"{t.limit * 100:g}%", "endpoint=${endpoint}")
        else:
            report.add(item, "unsupported", "no LocustLibrary check for this metric")
            continue
        report.add(item, "mapped", t.endpoint or "all requests")
        groups.setdefault(key, []).append(t.endpoint or "aggregated")
    if not groups:
        report.add("checks", "approximate", "k6 had no thresholds; the suite checks no request failed")
        return ["Should Have No Failures"], {}
    lines: list[str] = []
    lists: dict[str, list[str]] = {}
    for number, (key, endpoints) in enumerate(groups.items(), 1):
        call = _SEP.join(key)
        if len(endpoints) == 1:
            single = call.replace("${endpoint}", endpoints[0])
            lines.append(single.replace(f"{_SEP}endpoint=aggregated", ""))
            continue
        name = f"{prefix}_CHECK_{number}_ENDPOINTS"
        lists[name] = endpoints
        lines += [_SEP.join(["FOR", "${endpoint}", "IN", f"@{{{name}}}"]), _SEP + call, "END"]
    return lines, lists


def _variables(lists: dict[str, list[str]]) -> list[str]:
    if not lists:
        return []
    lines = ["*** Variables ***"]
    for name, items in lists.items():
        lines.append(f"@{{{name}}}" + _SEP + _SEP.join(items[:2]))
        lines += ["..." + _SEP + _SEP.join(items[i:i + 3]) for i in range(2, len(items), 3)]
    return [*lines, "", ""]


def _host(functions: list[ExecFunction], report: _Report) -> str:
    for call in (c for f in functions for c in f.calls):
        parts = urlsplit(call.url)
        if parts.scheme and parts.netloc:
            host = f"{parts.scheme}://{parts.netloc}"
            if _PLAIN_HOST.fullmatch(host):
                return host
            report.add("host", "set by hand",
                       f"script host is not a plain host[:port]; HOST defaults to {_DEFAULT_HOST}")
            return _DEFAULT_HOST
    report.add("host", "set by hand", f"no absolute URL found; HOST defaults to {_DEFAULT_HOST}")
    return _DEFAULT_HOST


def _suite(script: str, condition: str) -> str:
    stem, title = PurePath(script).stem, _title(script)
    return "\n".join([
        "*** Settings ***",
        f"Documentation       Load test converted from {script} by the LocustLibrary k6 converter.",
        f"...                 Every step lives in collections/{stem}_test_keywords.resource;",
        f"...                 reports/{stem}.k6-report.md lists what needs a hand port.",
        "Resource            ../resources/resources.resource", "",
        f"Test Tags           {stem}    load    slow", "", "",
        "*** Test Cases ***",
        f"{title} Load - {condition} - Thresholds Met",
        f"{_SEP}[Documentation]    Runs the {script} profile and passes when every converted check holds.",
        f"{_SEP}Test {title} Load",
    ]) + "\n"


def _keyword(name: str, doc: str, lines: list[str]) -> list[str]:
    return [name, f"{_SEP}[Documentation]    {doc}", *(_SEP + line for line in lines), ""]


def _keywords(script: str, insecure: bool, steps: _Steps) -> str:
    title = _title(script)
    create = _SEP.join(["Create Load Test", "${HOST}", f"verify_tls=${{{not insecure}}}",
                        "proxy=${PROXY}"])
    head = ["*** Settings ***",
            f"Documentation       Scenario keywords for the {script} load test.",
            f"...                 The suite calls only Test {title} Load.",
            "Resource            ../resources/resources.resource", "", "",
            *_variables(steps.lists),
            "*** Keywords ***"]
    body = [
        *_keyword(f"Test {title} Load", "Builds the users, runs the load, then checks it.",
                  [f"Build {title} Users", f"Run {title} Load", f"Check {title} Load"]),
        *_keyword(f"Build {title} Users", "One user class per k6 scenario, weighted by its peak users.",
                  [create, *steps.classes]),
        *_keyword(f"Run {title} Load", "Runs the converted k6 load profile headless.", steps.load),
        *_keyword(f"Check {title} Load", "The converted k6 thresholds.", steps.checks),
    ]
    return "\n".join([*head, *body]).rstrip() + "\n"


def entry_point(collections: list[str]) -> str:
    """resources/resources.resource: the one file every suite and collection imports."""
    lines = ["*** Settings ***",
             "Documentation       Single entry point. Every suite and collection imports this file only.",
             "Library             LocustLibrary    python_path=${CURDIR}/python",
             "Resource            variables.resource",
             "Resource            ${ENV}_variables.resource",
             *(f"Resource            ../collections/{c}" for c in collections)]
    return "\n".join(lines) + "\n"


VARIABLES = """*** Settings ***
Documentation       Variables shared by every environment. Pick the environment with -v ENV:<name>.


*** Variables ***
${ENV}              dev
"""


def env_variables(env: str, host: str) -> str:
    """resources/<env>_variables.resource with the host the scripts call."""
    return "\n".join([
        "*** Settings ***",
        f"Documentation       Values for the {env} environment.", "", "",
        "*** Variables ***",
        f"${{HOST}}             {host}",
        "${PROXY}            ${EMPTY}",
    ]) + "\n"


def _tasks_module(script: str, wanted: list[tuple[str, ExecFunction | None]]) -> str:
    parts = [repr(f"Tasks converted from {script}. Each function gets the Locust user."),
             "", "from typing import Any"]
    for name, fn in wanted:
        parts += ["", "", f"def {name}(user: Any) -> None:", *_function_body(script, name, fn)]
    return "\n".join(parts) + "\n"


def _function_body(script: str, name: str, fn: ExecFunction | None) -> list[str]:
    if fn is None or not fn.simple:
        why = fn.reason if fn else f"exec function {name} not found"
        line = fn.line if fn else 0
        # The reason quotes k6 source, so repr keeps it a plain string literal.
        return [f"    {f'Hand port from {script} line {line}: {why}.'!r}",
                f"    raise NotImplementedError({f'hand port: {script} line {line}'!r})"]
    return [_call_line(call) for call in fn.calls] or ["    del user"]


def _call_line(call: HttpCall) -> str:
    args = [repr(call.url)]
    if isinstance(call.body, str):
        args.append(f"data={call.body!r}")
    elif call.body is not None:
        args.append(f"json={call.body!r}")
    if call.headers:
        args.append(f"headers={call.headers!r}")
    args.append(f"name={(call.endpoint or call.url)!r}")
    verb = "delete" if call.method == "DELETE" else call.method.lower()
    return f"    user.client.{verb}({', '.join(args)})"
