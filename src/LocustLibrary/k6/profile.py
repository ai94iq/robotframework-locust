"""Map k6 scenarios and thresholds onto LocustLibrary keyword lines, noting each
choice in the conversion report.
"""

from dataclasses import dataclass, field

from .options import K6Scenario, Threshold
from .scan import ExecFunction

SEP = "    "
_PERCENTILES = {"p50", "p90", "p95", "p99", "p999"}


@dataclass
class Report:
    rows: list[tuple[str, str, str]] = field(default_factory=list)

    def add(self, item: str, status: str, note: str) -> None:
        self.rows.append((item, status, note.replace("|", "/")))

    def markdown(self, script: str) -> str:
        lines = [f"# k6 conversion report: {script}", "", "| Item | Status | Note |", "|---|---|---|"]
        return "\n".join([*lines, *(f"| {a} | {b} | {c} |" for a, b, c in self.rows)]) + "\n"


@dataclass(frozen=True, slots=True)
class Steps:
    classes: list[str]
    load: list[str]
    checks: list[str]
    condition: str
    lists: dict[str, list[str]]


def _peak(scenario: K6Scenario) -> int:
    if scenario.stages:
        return max(stage.users for stage in scenario.stages)
    return scenario.vus or scenario.max_vus


def classes(scenarios: tuple[K6Scenario, ...], by_name: dict[str, ExecFunction],
            module: str, report: Report) -> list[str]:
    lines: list[str] = []
    for s in scenarios:
        fn = by_name.get(s.exec_name)
        think = f"{fn.think_s if fn else 0:g}s"
        lines += [f"Add User Class{SEP}{s.name}{SEP}weight={max(1, _peak(s))}",
                  f"Set Wait Time{SEP}{think}{SEP}{think}",
                  f"Add Python Task{SEP}{s.exec_name}{SEP}{module}.{s.exec_name}"]
        if fn is None:
            report.add(f"scenario {s.name}", "hand port", f"exec function {s.exec_name} not found")
        elif fn.simple:
            report.add(f"scenario {s.name}", "mapped", f"{len(fn.calls)} HTTP calls")
        else:
            report.add(f"scenario {s.name}", "hand port", fn.reason)
    return lines


def load(scenarios: tuple[K6Scenario, ...], max_users: int,
         report: Report) -> tuple[list[str], str]:
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
    return [SEP.join(["Run Load Test", *args, f"max_users={max_users}"])], condition


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def _staged(scenarios: tuple[K6Scenario, ...], max_users: int,
            report: Report) -> tuple[list[str], str]:
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
    stages = SEP.join(f"{st.seconds:g}s:{t}" for st, t in zip(first, scaled, strict=True))
    lines = [f"Set Load Stages{SEP}{stages}", f"Run Load Test{SEP}max_users={max_users}"]
    return lines, f"Ramp To {_count(max(scaled, default=0), 'User')}"


def checks(thresholds: tuple[Threshold, ...], prefix: str,
           report: Report) -> tuple[list[str], dict[str, list[str]]]:
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
        call = SEP.join(key)
        if len(endpoints) == 1:
            single = call.replace("${endpoint}", endpoints[0])
            lines.append(single.replace(f"{SEP}endpoint=aggregated", ""))
            continue
        name = f"{prefix}_CHECK_{number}_ENDPOINTS"
        lists[name] = endpoints
        lines += [SEP.join(["FOR", "${endpoint}", "IN", f"@{{{name}}}"]), SEP + call, "END"]
    return lines, lists
