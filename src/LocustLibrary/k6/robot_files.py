"""Write the Robot suite, keyword resource, entry resources and Python tasks module
of a converted k6 project.
"""

from pathlib import PurePath

from robot.utils import escape

from .profile import SEP, Steps
from .scan import ExecFunction, HttpCall


def _title(script: str) -> str:
    return " ".join(PurePath(script).stem.replace("_", " ").split()).title()


def _variables(lists: dict[str, list[str]]) -> list[str]:
    if not lists:
        return []
    lines = ["*** Variables ***"]
    for name, items in lists.items():
        lines.append(f"@{{{name}}}" + SEP + SEP.join(items[:2]))
        lines += ["..." + SEP + SEP.join(items[i:i + 3]) for i in range(2, len(items), 3)]
    return [*lines, "", ""]


def suite(script: str, condition: str) -> str:
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
        f"{SEP}[Documentation]    Runs the {script} profile and passes when every converted check holds.",
        f"{SEP}Test {title} Load",
    ]) + "\n"


def _keyword(name: str, doc: str, lines: list[str]) -> list[str]:
    return [name, f"{SEP}[Documentation]    {doc}", *(SEP + line for line in lines), ""]


def keywords(script: str, insecure: bool, steps: Steps) -> str:
    title = _title(script)
    create = SEP.join(["Create Load Test", "${HOST}", f"verify_tls=${{{not insecure}}}",
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
        f"Documentation       Values for the {escape(env)} environment.", "", "",
        "*** Variables ***",
        f"${{HOST}}             {escape(host)}",
        "${PROXY}            ${EMPTY}",
    ]) + "\n"


def tasks_module(script: str, wanted: list[tuple[str, ExecFunction | None]]) -> str:
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
