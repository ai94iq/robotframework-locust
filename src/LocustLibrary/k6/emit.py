"""Turn k6 options and scanned functions into a Robot project, following the four-layer
house layout: a thin suite in tests/, its steps in collections/, one entry resource, the
Python tasks under resources/python/, and a report of what needs a hand port.
"""

import re
from dataclasses import dataclass
from pathlib import PurePath
from urllib.parse import urlsplit

from . import profile, robot_files
from .options import K6Options
from .robot_files import VARIABLES, entry_point, env_variables
from .scan import ExecFunction

__all__ = ["VARIABLES", "Conversion", "convert", "entry_point", "env_variables"]

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


def convert(script: str, opts: K6Options, functions: list[ExecFunction],
            max_users: int = 100) -> Conversion:
    """Map what k6 and LocustLibrary share; list the rest as hand port or unsupported."""
    if not _SCRIPT_NAME.fullmatch(PurePath(script).name):
        raise ValueError(f"unsupported script name {script!r}")
    report = profile.Report()
    stem = PurePath(script).stem
    by_name = {f.name: f for f in functions}
    load, condition = profile.load(opts.scenarios, max_users, report)
    load.append(f"Export Report{profile.SEP}{stem}")
    for metric, expr in opts.unparsed_thresholds:
        report.add(f"threshold {metric}", "unsupported", f"cannot read {expr}")
    checks, lists = profile.checks(opts.thresholds, stem.upper(), report)
    classes = profile.classes(opts.scenarios, by_name, f"{stem}_tasks", report)
    steps = profile.Steps(classes, load, checks, condition, lists)
    host = _host(functions, report)
    names = list(dict.fromkeys(s.exec_name for s in opts.scenarios))
    files = {
        f"tests/{stem}.robot": robot_files.suite(script, steps.condition),
        f"collections/{stem}_test_keywords.resource": robot_files.keywords(script, opts.insecure, steps),
        f"resources/python/{stem}_tasks.py": robot_files.tasks_module(
            script, [(n, by_name.get(n)) for n in names]),
        f"reports/{stem}.k6-report.md": report.markdown(script),
    }
    return Conversion(files, host)


def _host(functions: list[ExecFunction], report: profile.Report) -> str:
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
