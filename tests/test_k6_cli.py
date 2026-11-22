"""The CLI writes the project files and never runs k6 load."""

import json
from pathlib import Path
from typing import Any

import pytest

from LocustLibrary.k6 import cli

FIXTURES = Path(__file__).parent / "fixtures" / "k6"
SCRIPT = 'export default function () { http.get("https://h/x", { tags: { endpoint: "x" } }); }'


def _inspect(seen: dict[str, Any]) -> Any:
    def inspect(path: Path, env: dict[str, str]) -> dict[str, Any]:
        seen.update(path=path, env=env)
        return json.loads((FIXTURES / "smoke.inspect.json").read_text(encoding="utf-8"))

    return inspect


def test_cli_writes_the_project(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    seen: dict[str, Any] = {}
    monkeypatch.setattr(cli, "run_inspect", _inspect(seen))
    out = tmp_path / "robot"
    assert cli.main([str(script), "--trust-script", "--out", str(out), "-e", "RUN_ID=r1", "--max-users", "5"]) == 0
    written = sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file())
    assert written == ["collections/smoke_test_keywords.resource", "reports/smoke.k6-report.md",
                       "resources/dev_variables.resource", "resources/python/smoke_tasks.py",
                       "resources/resources.resource", "resources/variables.resource",
                       "tests/smoke.robot"]
    assert seen == {"path": script, "env": {"RUN_ID": "r1"}}
    assert "https://h" in (out / "resources/dev_variables.resource").read_text(encoding="utf-8")
    assert "max_users=5" in (out / "collections/smoke_test_keywords.resource").read_text(encoding="utf-8")


def test_env_file_is_kept_and_entry_lists_every_collection(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    out = tmp_path / "robot"
    (out / "resources").mkdir(parents=True)
    (out / "resources/dev_variables.resource").write_text("hand edited", encoding="utf-8")
    for name in ("smoke", "token"):
        script = tmp_path / f"{name}.js"
        script.write_text(SCRIPT, encoding="utf-8")
        cli.main([str(script), "--trust-script", "--out", str(out)])
    entry = (out / "resources/resources.resource").read_text(encoding="utf-8")
    assert "../collections/smoke_test_keywords.resource" in entry
    assert "../collections/token_test_keywords.resource" in entry
    assert "LocustLibrary    python_path=${CURDIR}/python" in entry
    assert "_tasks.py" not in entry
    assert (out / "resources/dev_variables.resource").read_text(encoding="utf-8") == "hand edited\n${ALLOW_STUBS}      ${False}\n"


def test_tasks_file_is_kept_unless_forced(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "robot"
    tasks = out / "resources/python/smoke_tasks.py"
    report = out / "reports/smoke.k6-report.md"
    tasks.parent.mkdir(parents=True)
    tasks.write_text("hand ported", encoding="utf-8")
    cli.main([str(script), "--trust-script", "--out", str(out)])
    assert tasks.read_text(encoding="utf-8") == "hand ported"
    assert "| tasks file | kept |" in report.read_text(encoding="utf-8")
    assert (out / "tests/smoke.robot").is_file()
    cli.main([str(script), "--trust-script", "--out", str(out), "--force"])
    assert tasks.read_text(encoding="utf-8") != "hand ported"
    assert "| tasks file | kept |" not in report.read_text(encoding="utf-8")


def test_force_backs_up_the_tasks_file(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "robot"
    tasks = out / "resources/python/smoke_tasks.py"
    backup = out / "resources/python/smoke_tasks.py.bak"
    tasks.parent.mkdir(parents=True)
    backup.write_text("older backup", encoding="utf-8")
    tasks.write_text("hand ported", encoding="utf-8")
    cli.main([str(script), "--trust-script", "--out", str(out), "--force"])
    assert backup.read_text(encoding="utf-8") == "older backup"
    assert (out / "resources/python/smoke_tasks.py.bak.1").read_text(encoding="utf-8") == "hand ported"
    report = (out / "reports/smoke.k6-report.md").read_text(encoding="utf-8")
    assert "| tasks file | backed up | old resources/python/smoke_tasks.py copied to " \
        "resources/python/smoke_tasks.py.bak.1 before the rewrite |" in report


def test_a_second_force_keeps_the_first_backup(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "robot"
    tasks = out / "resources/python/smoke_tasks.py"
    tasks.parent.mkdir(parents=True)
    tasks.write_text("hand ported", encoding="utf-8")
    cli.main([str(script), "--trust-script", "--out", str(out), "--force"])
    cli.main([str(script), "--trust-script", "--out", str(out), "--force"])
    assert (out / "resources/python/smoke_tasks.py.bak").read_text(encoding="utf-8") == "hand ported"
    assert not (out / "resources/python/smoke_tasks.py.bak.1").exists()


def test_a_missing_script_is_reported_as_missing(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="no such file"):
        cli.main([str(tmp_path / "gone.js")])


def test_allow_stubs_with_no_value_is_not_added_again(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    out = tmp_path / "robot"
    env = out / "resources/dev_variables.resource"
    env.parent.mkdir(parents=True)
    env.write_text("${ALLOW_STUBS}\n", encoding="utf-8")
    cli.main([str(script), "--trust-script", "--out", str(out)])
    assert env.read_text(encoding="utf-8") == "${ALLOW_STUBS}\n"


def test_bad_env_pair_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        cli.main([str(tmp_path / "a.js"), "-e", "NOEQUALS"])


# The env name lands in a file name and a Robot Settings line, so a newline would add a line.
@pytest.mark.parametrize("name", ["dev\nLibrary    OperatingSystem", "../dev", "d v", ""])
def test_unsafe_env_name_is_rejected(monkeypatch, tmp_path: Path, name: str) -> None:
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    with pytest.raises(SystemExit):
        cli.main([str(tmp_path / "a.js"), "--trust-script", "--env-name", name])


def test_inspect_needs_trust_script(monkeypatch, tmp_path: Path) -> None:
    called: dict[str, Any] = {}
    monkeypatch.setattr(cli, "run_inspect", _inspect(called))
    (tmp_path / "a.js").write_text("export default function () {}", encoding="utf-8")
    with pytest.raises(SystemExit) as stop:
        cli.main([str(tmp_path / "a.js"), "--out", str(tmp_path / "out")])
    err = str(stop.value.code)
    assert "\n" not in err
    assert "k6 inspect runs the script's init code" in err and "--trust-script" in err
    assert not called


def test_host_flag_sets_the_env_file(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    out = tmp_path / "robot"
    assert cli.main([str(script), "--trust-script", "--out", str(out), "--host", "http://staging:81"]) == 0
    assert "http://staging:81" in (out / "resources/dev_variables.resource").read_text(encoding="utf-8")


def test_host_flag_updates_a_kept_env_file(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    out = tmp_path / "robot"
    env = out / "resources/dev_variables.resource"
    assert cli.main([str(script), "--trust-script", "--out", str(out)]) == 0
    env.write_text(env.read_text(encoding="utf-8") + "${TOKEN}            kept\n", encoding="utf-8")
    assert cli.main([str(script), "--trust-script", "--out", str(out), "--host", "http://staging:81"]) == 0
    text = env.read_text(encoding="utf-8")
    assert "${HOST}             http://staging:81\n" in text
    assert "${ALLOWED_HOSTS}      staging\n" in text
    assert "https://h" not in text and "${TOKEN}            kept" in text
    assert "| host | set by --host | http://staging:81 |" in (out / "reports/smoke.k6-report.md").read_text(encoding="utf-8")


def test_host_flag_on_env_file_without_host_lines_is_reported(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    monkeypatch.setattr(cli, "run_inspect", _inspect({}))
    out = tmp_path / "robot"
    env = out / "resources/dev_variables.resource"
    env.parent.mkdir(parents=True)
    env.write_text("hand edited", encoding="utf-8")
    assert cli.main([str(script), "--trust-script", "--out", str(out), "--host", "http://staging:81"]) == 0
    assert env.read_text(encoding="utf-8") == "hand edited\n${ALLOW_STUBS}      ${False}\n"
    report = (out / "reports/smoke.k6-report.md").read_text(encoding="utf-8")
    assert "| host | not applied | resources/dev_variables.resource has no ${HOST} or ${ALLOWED_HOSTS} line; set them there by hand |" in report


def test_bad_host_flag_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        cli.main([str(tmp_path / "x.js"), "--trust-script", "--host", "ftp://x"])


def test_a_shortcut_conflict_gets_its_own_error_not_an_inspect_hint(tmp_path: Path) -> None:
    script = tmp_path / "clash.js"
    script.write_text("export const options = { iterations: 5, stages: [{ duration: '1s', target: 1 }] };\n" + SCRIPT,
                      encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        cli.main([str(script), "--out", str(tmp_path / "robot")])
    message = str(caught.value)
    assert "`iterations` and `stages`" in message
    assert "inspect" not in message and "--trust-script" not in message


@pytest.mark.parametrize("bare", ["${HOST}", "${ALLOWED_HOSTS}"])
def test_a_host_line_with_no_value_is_still_rewritten(tmp_path: Path, bare: str) -> None:
    env = tmp_path / "dev_variables.resource"
    env.write_text(f"hand edited\n{bare}\n", encoding="utf-8")
    assert cli._set_host(env, "https://new.example") is True
    lines = env.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "hand edited"
    assert lines[1].startswith(bare) and lines[1] != bare
    assert "new.example" in lines[1]
