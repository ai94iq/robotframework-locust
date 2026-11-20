"""Read a k6 script's resolved options through `k6 inspect`, never `k6 run`."""

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..scenario import Stage

_DURATION_PART = re.compile(r"(\d+(?:\.\d+)?)(ms|h|m|s)")
_UNIT_SECONDS = {"ms": 0.001, "s": 1.0, "m": 60.0, "h": 3600.0}
_METRIC = re.compile(r"^(\w+)(?:\{endpoint:([^}]*)\})?$")
_EXPR = re.compile(r"^(p\((\d+(?:\.\d+)?)\)|avg|med|min|max|rate)\s*<=?\s*(\d+(?:\.\d+)?)$")


@dataclass(frozen=True, slots=True)
class K6Scenario:
    """One k6 scenario as `k6 inspect` resolves it."""

    name: str
    executor: str
    exec_name: str = "default"
    stages: tuple[Stage, ...] = ()
    vus: int = 0
    iterations: int = 0
    duration_s: float = 0.0
    rate: float = 0.0
    max_vus: int = 0


@dataclass(frozen=True, slots=True)
class Threshold:
    """`stat` is p95, p999, avg, med, min, max or rate; `endpoint` "" means every request."""

    metric: str
    endpoint: str
    stat: str
    limit: float


@dataclass(frozen=True, slots=True)
class K6Options:
    scenarios: tuple[K6Scenario, ...]
    thresholds: tuple[Threshold, ...]
    insecure: bool
    total_s: float
    max_vus: int


def go_seconds(text: str) -> float:
    """Seconds in a Go duration as k6 prints it, such as 2m0s or 500ms."""
    parts = _DURATION_PART.findall(text)
    if not parts or "".join(n + u for n, u in parts) != text:
        raise ValueError(f"bad duration {text!r}")
    return sum(float(n) * _UNIT_SECONDS[u] for n, u in parts)


def _threshold(metric: str, expr: str) -> Threshold:
    name, expr_match = _METRIC.match(metric), _EXPR.match(expr.strip())
    if name is None or expr_match is None:
        raise ValueError(f"unsupported threshold {metric}: {expr}")
    percentile = expr_match.group(2)
    stat = "p" + percentile.replace(".", "") if percentile else expr_match.group(1)
    return Threshold(name.group(1), name.group(2) or "", stat, float(expr_match.group(3)))


def parse_thresholds(raw: dict[str, list[str]] | None) -> tuple[Threshold, ...]:
    return tuple(_threshold(m, e) for m, exprs in sorted((raw or {}).items()) for e in exprs)


def _rate(raw: dict[str, Any]) -> float:
    if not raw.get("rate"):
        return 0.0
    return float(raw["rate"]) / go_seconds(raw.get("timeUnit") or "1s")


def _scenario(name: str, raw: dict[str, Any]) -> K6Scenario:
    stages = tuple(Stage(go_seconds(s["duration"]), int(s["target"]))
                   for s in raw.get("stages") or [])
    return K6Scenario(
        name=name,
        executor=raw["executor"],
        exec_name=raw.get("exec") or "default",
        stages=stages,
        vus=int(raw.get("vus") or 0),
        iterations=int(raw.get("iterations") or 0),
        duration_s=go_seconds(raw["duration"]) if raw.get("duration") else 0.0,
        rate=_rate(raw),
        max_vus=int(raw.get("maxVUs") or 0),
    )


def parse_options(data: dict[str, Any]) -> K6Options:
    scenarios = data.get("scenarios") or {}
    return K6Options(
        scenarios=tuple(_scenario(n, scenarios[n]) for n in sorted(scenarios)),
        thresholds=parse_thresholds(data.get("thresholds")),
        insecure=bool(data.get("insecureSkipTLSVerify")),
        total_s=go_seconds(data["totalDuration"]) if data.get("totalDuration") else 0.0,
        max_vus=int(data.get("maxVUs") or 0),
    )


def run_inspect(script: Path, env: dict[str, str], timeout: int = 60) -> dict[str, Any]:
    """k6 runs only the script's init code here; no request is sent."""
    k6 = shutil.which("k6")
    if k6 is None:
        raise FileNotFoundError("k6 is not on PATH; k6 inspect is needed to read options")
    env_args = [arg for key, value in sorted(env.items()) for arg in ("-e", f"{key}={value}")]
    done = subprocess.run([k6, "inspect", "--execution-requirements", *env_args, str(script)],
                          capture_output=True, text=True, timeout=timeout, check=True)
    result: dict[str, Any] = json.loads(done.stdout)
    return result
