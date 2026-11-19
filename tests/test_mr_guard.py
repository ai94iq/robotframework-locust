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
    assert any("127.0.0.1" in item for item in problems)
    assert any("worker" in item for item in problems)


def test_second_public_host_and_missing_worker_dial_fail() -> None:
    public = '''
_LOOPBACK = "127.0.0.1"
master = ["--master", "--web-host", _LOOPBACK, "--web-host", "0.0.0.0", "--master-bind-host", _LOOPBACK]
worker = ["--worker", "--master-host", _LOOPBACK]
'''
    assert any("public" in item or "web-host" in item for item in mr_guard.spawn_problems(public))
    missing = '''
_LOOPBACK = "127.0.0.1"
master = ["--master", "--master-bind-host", _LOOPBACK, "--web-host", _LOOPBACK]
worker = ["--worker"]
'''
    assert any("master-host" in item for item in mr_guard.spawn_problems(missing))


def test_public_web_and_login_fail() -> None:
    source = '_LOOPBACK = {"0.0.0.0"}\ncmd = ["--web-login"]\n'
    assert mr_guard.web_problems(source)


def test_swallowed_error_and_shell_fail() -> None:
    source = "try:\n    run()\nexcept Exception:\n    pass\nPopen(cmd, shell=True)\n"
    assert mr_guard.slop_problems(source, "bad.py")


def test_test_must_not_start_locust() -> None:
    source = 'subprocess.Popen([sys.executable, "-m", "locust"])\n'
    assert mr_guard.test_spawn_problems(source, "test_bad.py")
    shell = 'import os\nos.system("python -m locust")\n'
    assert mr_guard.test_spawn_problems(shell, "test_bad.py")
    swallowed = "try:\n    run()\nexcept Exception:\n    return\n"
    assert mr_guard.slop_problems(swallowed, "bad.py")


def test_web_comment_is_not_a_bind() -> None:
    source = (
        '"""Do not pass --web-login or 0.0.0.0."""\n'
        '_LOOPBACK = {"127.0.0.1", "localhost", "::1"}\n'
    )
    assert mr_guard.web_problems(source) == []
