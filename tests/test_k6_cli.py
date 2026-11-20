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
    assert cli.main([str(script), "--out", str(out), "-e", "RUN_ID=r1", "--max-users", "5"]) == 0
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
        cli.main([str(script), "--out", str(out)])
    entry = (out / "resources/resources.resource").read_text(encoding="utf-8")
    assert "../collections/smoke_test_keywords.resource" in entry
    assert "../collections/token_test_keywords.resource" in entry
    assert "LocustLibrary    python_path=${CURDIR}/python" in entry
    assert "_tasks.py" not in entry
    assert (out / "resources/dev_variables.resource").read_text(encoding="utf-8") == "hand edited"


def test_bad_env_pair_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        cli.main([str(tmp_path / "a.js"), "-e", "NOEQUALS"])
