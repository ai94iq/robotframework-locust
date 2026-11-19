"""Fail a change that drops the library quality bar."""

import ast
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def check(root: Path) -> list[str]:
    problems: list[str] = []
    problems.extend(coverage_problems((root / "pyproject.toml").read_text(encoding="utf-8")))
    problems.extend(spawn_problems((root / "src/LocustLibrary/distributed.py").read_text(encoding="utf-8")))
    problems.extend(web_problems((root / "src/LocustLibrary/webui.py").read_text(encoding="utf-8")))
    runner = (root / "src/LocustLibrary/runner.py").read_text(encoding="utf-8")
    library = (root / "src/LocustLibrary/__init__.py").read_text(encoding="utf-8")
    problems.extend(patch_problems(runner))
    problems.extend(time_problems(runner, "_parse_time"))
    problems.extend(time_problems(library, "_parse_seconds"))
    for path in (root / "src").rglob("*.py"):
        problems.extend(slop_problems(path.read_text(encoding="utf-8"), path.name))
    for path in (root / "tests").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        problems.extend(slop_problems(text, path.name))
        problems.extend(test_spawn_problems(text, path.name))
    return problems


def coverage_problems(text: str) -> list[str]:
    data = tomllib.loads(text)
    report = data["tool"]["coverage"]["report"]
    omit = data["tool"]["coverage"]["run"].get("omit") or []
    problems: list[str] = []
    if int(report["fail_under"]) < 80:
        problems.append("fail_under must stay at 80 or higher")
    if "src/LocustLibrary/studio/*" not in omit:
        problems.append("studio must stay outside the unit coverage gate")
    for item in omit:
        if item in {"src/LocustLibrary", "src/LocustLibrary/*"}:
            problems.append(f"coverage omit hides the library: {item}")
    return problems


def spawn_problems(source: str) -> list[str]:
    tree = ast.parse(source)
    problems: list[str] = []
    if _loopback_value(tree) != "127.0.0.1":
        problems.append("loopback constant must be 127.0.0.1")
    saw_master = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue
        strings = _strings(node)
        if "--master" in strings and "--worker" not in strings:
            saw_master = True
            problems.extend(_needs_loopback(node, strings, "--master-bind-host"))
            problems.extend(_needs_loopback(node, strings, "--web-host"))
        if "--worker" in strings and "--web-host" in strings:
            problems.append("worker argv must not pass --web-host")
    if not saw_master:
        problems.append("master spawn argv was not found")
    return problems


def web_problems(source: str) -> list[str]:
    problems = [f"web UI allow list is missing {host}" for host in _LOOPBACK_HOSTS if host not in source]
    if "0.0.0.0" in source or "--web-login" in source:
        problems.append("web UI must not bind a public host or pass --web-login")
    return problems


def patch_problems(source: str) -> list[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "run_load_test":
            calls = [n.func.id for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
            if "_patch_gevent" in calls:
                return []
    return ["run_load_test must call _patch_gevent"]


def time_problems(source: str, name: str) -> list[str]:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            text = ast.get_source_segment(source, node) or ""
            ms = text.find('endswith("ms")')
            sec = text.find('endswith("s")')
            if ms != -1 and sec != -1 and ms < sec:
                return []
    return [f"{name} must check ms before s"]


def slop_problems(source: str, name: str) -> list[str]:
    problems: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ExceptHandler) and _swallows(node):
            problems.append(f"{name}: exception swallowed")
        if isinstance(node, ast.Call) and _shell_true(node):
            problems.append(f"{name}: shell=True")
    return problems


def test_spawn_problems(source: str, name: str) -> list[str]:
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        strings = _strings(node)
        if "-m" in strings and "locust" in strings:
            return [f"{name}: test starts locust"]
    return []


def _loopback_value(tree: ast.AST) -> str | None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            value = node.value
            if (
                isinstance(target, ast.Name)
                and target.id == "_LOOPBACK"
                and isinstance(value, ast.Constant)
                and isinstance(value.value, str)
            ):
                return value.value
    return None


def _needs_loopback(node: ast.List, strings: list[str], flag: str) -> list[str]:
    names = [elt.id for elt in node.elts if isinstance(elt, ast.Name)]
    if flag in strings and "_LOOPBACK" in names:
        return []
    return [f"master argv must pass {flag} 127.0.0.1"]


def _strings(node: ast.AST) -> list[str]:
    found: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            found.append(child.value)
    return found


def _swallows(node: ast.ExceptHandler) -> bool:
    return len(node.body) == 1 and isinstance(node.body[0], ast.Pass)


def _shell_true(node: ast.Call) -> bool:
    return any(kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True for kw in node.keywords)


def main() -> int:
    problems = check(ROOT)
    for item in problems:
        print(item)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
