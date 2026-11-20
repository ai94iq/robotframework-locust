"""Turn k6 options and scanned functions into a Robot suite, a tasks module and a report."""

from dataclasses import dataclass, field
from pathlib import PurePath
from urllib.parse import urlsplit

from .options import K6Options, K6Scenario, Threshold
from .scan import ExecFunction, HttpCall

_SEP = "    "
_PERCENTILES = {"p50", "p90", "p95", "p99", "p999"}
_DEFAULT_HOST = "http://127.0.0.1"


@dataclass(frozen=True, slots=True)
class Conversion:
    robot: str
    tasks: str
    report: str


@dataclass
class _Report:
    rows: list[tuple[str, str, str]] = field(default_factory=list)

    def add(self, item: str, status: str, note: str) -> None:
        self.rows.append((item, status, note.replace("|", "/")))

    def markdown(self, script: str) -> str:
        lines = [f"# k6 conversion report: {script}", "", "| Item | Status | Note |", "|---|---|---|"]
        return "\n".join([*lines, *(f"| {a} | {b} | {c} |" for a, b, c in self.rows)]) + "\n"


def convert(script: str, opts: K6Options, functions: list[ExecFunction],
            max_users: int = 100) -> Conversion:
    """Map what k6 and LocustLibrary share; list the rest as hand port or unsupported."""
    report = _Report()
    module = PurePath(script).stem + "_tasks"
    by_name = {f.name: f for f in functions}
    body = [*_classes(opts.scenarios, by_name, module, report),
            *_load(opts.scenarios, max_users, report),
            *_checks(opts.thresholds, report)]
    robot = _suite(script, module, _host(functions, report), opts.insecure, body)
    names = list(dict.fromkeys(s.exec_name for s in opts.scenarios))
    tasks = _tasks_module(script, [(n, by_name.get(n)) for n in names])
    return Conversion(robot, tasks, report.markdown(script))


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


def _load(scenarios: tuple[K6Scenario, ...], max_users: int, report: _Report) -> list[str]:
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
    return [_SEP.join(["Run Load Test", *args, "max_users=${MAX_USERS}"])]


def _staged(scenarios: tuple[K6Scenario, ...], max_users: int, report: _Report) -> list[str]:
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
    stages = _SEP.join(f"{st.seconds:g}s:{round(t * scale)}" for st, t in zip(first, totals, strict=True))
    return [f"Set Load Stages{_SEP}{stages}", f"Run Load Test{_SEP}max_users=${{MAX_USERS}}"]


def _checks(thresholds: tuple[Threshold, ...], report: _Report) -> list[str]:
    lines: list[str] = []
    for t in thresholds:
        item = f"threshold {t.metric} {t.stat}"
        if t.metric == "http_req_duration" and t.stat in _PERCENTILES:
            where = t.endpoint or "aggregated"
            lines.append(_SEP.join(["Should Meet Response Time", where, t.stat, f"{t.limit:g}ms"]))
        elif t.metric == "http_req_failed" and t.stat == "rate":
            endpoint = [f"endpoint={t.endpoint}"] if t.endpoint else []
            lines.append(_SEP.join(["Should Meet Error Rate", f"{t.limit * 100:g}%", *endpoint]))
        else:
            report.add(item, "unsupported", "no LocustLibrary check for this metric")
            continue
        report.add(item, "mapped", t.endpoint or "all requests")
    return lines


def _host(functions: list[ExecFunction], report: _Report) -> str:
    for call in (c for f in functions for c in f.calls):
        parts = urlsplit(call.url)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    report.add("host", "set by hand", f"no absolute URL found; HOST defaults to {_DEFAULT_HOST}")
    return _DEFAULT_HOST


def _suite(script: str, module: str, host: str, insecure: bool, body: list[str]) -> str:
    title = PurePath(script).stem.replace("_", " ").title()
    head = [
        "*** Settings ***",
        f"Documentation     Converted from {script} by the LocustLibrary k6 converter.",
        f"...               Run with --pythonpath set to the folder of {module}.py.",
        f"...               {PurePath(script).stem}.report.md lists what needs a hand port.",
        "Library           LocustLibrary", "",
        "*** Variables ***",
        f"${{HOST}}           {host}",
        "${PROXY}          ${EMPTY}",
        "${MAX_USERS}      100", "",
        "*** Test Cases ***",
        f"{title} Load Test",
        f"{_SEP}Create Load Test{_SEP}${{HOST}}{_SEP}verify_tls=${{{not insecure}}}{_SEP}proxy=${{PROXY}}",
    ]
    return "\n".join([*head, *(_SEP + line for line in body)]) + "\n"


def _tasks_module(script: str, wanted: list[tuple[str, ExecFunction | None]]) -> str:
    parts = [f'"""Tasks converted from {script}. Each function gets the Locust user."""',
             "", "from typing import Any"]
    for name, fn in wanted:
        parts += ["", "", f"def {name}(user: Any) -> None:", *_function_body(script, name, fn)]
    return "\n".join(parts) + "\n"


def _function_body(script: str, name: str, fn: ExecFunction | None) -> list[str]:
    if fn is None or not fn.simple:
        why = fn.reason if fn else f"exec function {name} not found"
        line = fn.line if fn else 0
        return [f'    """Hand port from {script} line {line}: {why}."""',
                f'    raise NotImplementedError("hand port: {script} line {line}")']
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
