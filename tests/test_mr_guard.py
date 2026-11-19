"""The merge-request hook rejects a dropped quality bar."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "mr_guard", ROOT / "evals" / "hooks" / "mr_guard.py"
)
assert _SPEC is not None and _SPEC.loader is not None
mr_guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(mr_guard)


def test_repo_holds_the_bar() -> None:
    assert mr_guard.check(ROOT) == []


def test_lower_coverage_gate_fails() -> None:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    broken = text.replace("fail_under = 80", "fail_under = 10")
    assert any("fail_under" in item for item in mr_guard.coverage_problems(broken))


def test_public_master_bind_fails() -> None:
    source = '''
_LOOPBACK = "0.0.0.0"
def run():
    master = ["--master", "--master-bind-host", _LOOPBACK]
    worker = ["--worker", "--web-host", _LOOPBACK]
'''
    problems = mr_guard.spawn_problems(source)
    assert any("master argv" in item for item in problems)
    assert any("worker" in item for item in problems)


def test_public_web_and_login_fail() -> None:
    source = '_LOOPBACK = {"0.0.0.0"}\ncmd = ["--web-login"]\n'
    assert mr_guard.web_problems(source)


def test_swallowed_error_and_shell_fail() -> None:
    source = "try:\n    run()\nexcept Exception:\n    pass\nPopen(cmd, shell=True)\n"
    assert mr_guard.slop_problems(source, "bad.py")


def test_test_must_not_start_locust() -> None:
    source = 'subprocess.Popen([sys.executable, "-m", "locust"])\n'
    assert mr_guard.test_spawn_problems(source, "test_bad.py")
