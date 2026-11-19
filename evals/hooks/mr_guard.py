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
    problems.extend(keyword_problems(library, runner))
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
            problems.extend(_flag_problems(node, "--master-bind-host"))
            problems.extend(_flag_problems(node, "--web-host"))
            if any(item in {"0.0.0.0", "*"} for item in strings):
                problems.append("master argv has a public bind")
        if "--worker" in strings:
            if "--web-host" in strings:
                problems.append("worker argv must not pass --web-host")
            problems.extend(_flag_problems(node, "--master-host", "worker argv must pass --master-host 127.0.0.1"))
    if not saw_master:
        problems.append("master spawn argv was not found")
    return problems


def web_problems(source: str) -> list[str]:
    strings = _code_strings(ast.parse(source))
    problems = [f"web UI allow list is missing {host}" for host in _LOOPBACK_HOSTS if host not in strings]
    if "0.0.0.0" in strings or "--web-login" in strings:
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
        if isinstance(node, ast.Call) and _spawns_locust(node):
            return [f"{name}: test starts locust"]
    return []


def keyword_problems(library: str, runner: str) -> list[str]:
    lib = ast.parse(library)
    run = ast.parse(runner)
    problems: list[str] = []
    for name in ("add_task", "set_on_start", "set_on_stop"):
        if not _calls(lib, name, "_keyword_name"):
            problems.append(f"{name} must reject a blank keyword")
    if not _raises(lib, "_keyword_name"):
        problems.append("_keyword_name must raise when the name is empty")
    if not _calls(run, "_call_keyword", "run_keyword"):
        problems.append("RF tasks must call BuiltIn.run_keyword")
    return problems


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


def _flag_problems(node: ast.List, flag: str, message: str | None = None) -> list[str]:
    values = _flag_values(node.elts, flag)
    if values and all(_is_loopback(item) for item in values):
        return []
    return [message or f"master argv must pass {flag} 127.0.0.1"]


def _flag_values(elts: list[ast.expr], flag: str) -> list[ast.expr]:
    values: list[ast.expr] = []
    for index, elt in enumerate(elts):
        if isinstance(elt, ast.Constant) and elt.value == flag and index + 1 < len(elts):
            values.append(elts[index + 1])
    return values


def _is_loopback(node: ast.expr) -> bool:
    if isinstance(node, ast.Name) and node.id == "_LOOPBACK":
        return True
    return isinstance(node, ast.Constant) and node.value == "127.0.0.1"


def _strings(node: ast.AST) -> list[str]:
    found: list[str] = []
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            found.append(child.value)
    return found


def _swallows(node: ast.ExceptHandler) -> bool:
    if not _broad(node.type) or any(isinstance(child, ast.Raise) for child in ast.walk(node)):
        return False
    return all(isinstance(stmt, (ast.Pass, ast.Return, ast.Continue)) for stmt in node.body)


def _broad(expr: ast.expr | None) -> bool:
    if expr is None:
        return True
    if isinstance(expr, ast.Name):
        return expr.id in {"Exception", "BaseException"}
    if isinstance(expr, ast.Tuple):
        return any(_broad(item) for item in expr.elts)
    return False


def _spawns_locust(node: ast.Call) -> bool:
    name = node.func.id if isinstance(node.func, ast.Name) else ""
    if isinstance(node.func, ast.Attribute):
        name = node.func.attr
    if name not in {"system", "popen", "run", "call", "check_call", "check_output", "Popen"}:
        return False
    return "locust" in " ".join(_strings(node)).lower()


def _calls(tree: ast.AST, fn_name: str, callee: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            return any(_callee(call) == callee for call in ast.walk(node) if isinstance(call, ast.Call))
    return False


def _callee(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _raises(tree: ast.AST, fn_name: str) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            return any(isinstance(child, ast.Raise) for child in ast.walk(node))
    return False


def _code_strings(tree: ast.AST) -> set[str]:
    skipped = _docstrings(tree)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skipped:
            found.add(node.value)
    return found


def _docstrings(tree: ast.AST) -> set[int]:
    skipped: set[int] = set()
    nodes = [tree, *(n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)))]
    for node in nodes:
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            skipped.add(id(body[0].value))
    return skipped


def _shell_true(node: ast.Call) -> bool:
    return any(kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True for kw in node.keywords)


def main() -> int:
    problems = check(ROOT)
    for item in problems:
        print(item)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
