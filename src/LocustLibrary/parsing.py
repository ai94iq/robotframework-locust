"""Parse keyword arguments: durations, stages, status lists, ratios and task targets."""

import importlib
from collections.abc import Callable
from typing import Any, cast

from .scenario import Stage, StatsRow


def _parse_seconds(value: str) -> float:
    value = value.strip().lower()
    if value.endswith("ms"):
        return float(value[:-2]) / 1000.0
    if value.endswith("s"):
        return float(value[:-1])
    if value.endswith("m"):
        return float(value[:-1]) * 60
    if value.endswith("h"):
        return float(value[:-1]) * 3600
    return float(value)


_PERCENTILE_FIELDS = {
    "50": "p50",
    "90": "p90",
    "95": "p95",
    "99": "p99",
    "999": "p999",
}


def _statuses(value: object) -> tuple[int, ...]:
    parts = value if isinstance(value, list | tuple) else str(value).split(",")
    codes = tuple(int(str(p).strip()) for p in parts if str(p).strip())
    if not codes:
        raise ValueError("expected status is required")
    return codes


def _stage(text: str) -> Stage:
    try:
        duration, users = text.split(":")
        stage = Stage(seconds=_parse_seconds(duration), users=int(users))
    except ValueError as err:
        raise ValueError(f"bad stage {text!r}: use duration:users, as 2m:20") from err
    if stage.users < 0 or stage.seconds <= 0:
        raise ValueError(f"bad stage {text!r}: users and duration must be positive")
    return stage


def _python_function(target: str) -> Callable[[Any], None]:
    module_name, _, attr = target.rpartition(".")
    if not module_name:
        raise ValueError(f"use module.function, got {target!r}")
    function = getattr(importlib.import_module(module_name), attr, None)
    if not callable(function):
        raise TypeError(f"{module_name} has no function {attr!r}")
    return cast("Callable[[Any], None]", function)


def _keyword_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("keyword name is required")
    return name


def _measured_percentile(row: StatsRow, percentile: str) -> float:
    if row.request_count == 0:
        raise RuntimeError("No requests recorded.")
    field = _PERCENTILE_FIELDS.get(percentile.lower().removeprefix("p"))
    if field is None:
        raise RuntimeError(f"Percentile not measured: {percentile}")
    return float(getattr(row, field))


def _ratio(value: object) -> float:
    """`20%` or `0.2` as a fraction."""
    text = str(value).strip()
    return float(text.rstrip("%")) / 100 if text.endswith("%") else float(text)
