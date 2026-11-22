"""Stop rules: end a run once a measured value stays past its limit for a whole window.

The rule text follows Taurus pass/fail criteria, for example `p95 > 1s for 10s, stop as failed`.
"""

import fnmatch
import re
from dataclasses import dataclass
from typing import Any

import psutil

_RULE = re.compile(
    r"^\s*(?P<metric>p\d+(?:\.\d+)?|fail|rc[\d?*]{1,3}|cpu|mem)\s*>\s*(?P<limit>\d+(?:\.\d+)?)"
    r"\s*(?P<unit>ms|s|%)?\s*(?:for\s+(?P<window>\d+(?:\.\d+)?)s)?"
    r"\s*(?:,\s*stop\s+as\s+(?P<status>failed|passed))?\s*$")


@dataclass
class StopRule:
    metric: str
    limit: float
    window: float
    fail_run: bool
    text: str


def parse_rule(text: str) -> StopRule:
    found = _RULE.match(text)
    timed = bool(found and found["metric"].startswith("p"))
    if not found or (found["unit"] == "%") == timed:
        raise ValueError(f"Stop rule '{text}' is not like 'p95 > 1s for 10s, stop as failed'; "
                         "metrics: pN, fail, rcNNN, cpu, mem")
    limit = float(found["limit"]) * (1000 if found["unit"] == "s" else 1)
    return StopRule(found["metric"], limit, float(found["window"] or 0),
                    found["status"] != "passed", text.strip())


def _share(digits: str) -> float:
    """p999 is the 99.9th percentile, as in the Should keywords; p99.9 reads the same."""
    if "." not in digits and len(digits) > 2:
        digits = f"{digits[:2]}.{digits[2:]}"
    return float(digits) / 100


class RuleWatch:
    """Checks every rule on each tick; the first rule that held for its window names the stop."""

    def __init__(self, rules: list[StopRule], local: Any) -> None:
        self.rules, self.local, self.failed = rules, local, False
        self._since: dict[int, float] = {}
        self._codes: list[int] = []
        self._seen = {"codes": 0, "requests": 0, "failures": 0}
        if any(rule.metric.startswith("rc") for rule in rules):
            local.environment.events.request.add_listener(self._record)

    def _record(self, response: Any = None, **_kwargs: Any) -> None:
        code = getattr(response, "status_code", None)
        if code is not None:
            self._codes.append(int(code))

    def check(self, elapsed: float) -> str:
        values = self._measure()
        for index, rule in enumerate(self.rules):
            value = values.get(rule.metric)
            if value is None:
                # A tick with no responses says nothing, so the window neither grows nor restarts.
                continue
            if value <= rule.limit:
                self._since.pop(index, None)
                continue
            start = self._since.setdefault(index, elapsed)
            if elapsed - start >= rule.window:
                self.failed = rule.fail_run
                return f"stopped after {elapsed:.0f} s: {rule.text}"
        return ""

    def _measure(self) -> dict[str, float | None]:
        needs_fail = any(rule.metric == "fail" for rule in self.rules)
        values: dict[str, float | None] = {"fail": self._fail_share()} if needs_fail else {}
        codes, self._seen["codes"] = self._codes[self._seen["codes"]:], len(self._codes)
        for rule in self.rules:
            if rule.metric.startswith("p"):
                share = _share(rule.metric[1:])
                values[rule.metric] = self.local.stats.total.get_current_response_time_percentile(share)
            elif rule.metric.startswith("rc") and codes:
                hits = sum(fnmatch.fnmatch(str(code), rule.metric[2:]) for code in codes)
                values[rule.metric] = 100 * hits / len(codes)
            elif rule.metric == "cpu":
                values["cpu"] = psutil.cpu_percent()
            elif rule.metric == "mem":
                values["mem"] = psutil.virtual_memory().percent
        return values

    def _fail_share(self) -> float | None:
        total = self.local.stats.total
        requests = total.num_requests - self._seen["requests"]
        failures = total.num_failures - self._seen["failures"]
        self._seen["requests"], self._seen["failures"] = total.num_requests, total.num_failures
        return 100 * failures / requests if requests else None
