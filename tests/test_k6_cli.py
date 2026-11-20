"""The CLI writes the three files next to each other and never runs k6 load."""

import json
from pathlib import Path
from typing import Any

import pytest

from LocustLibrary.k6 import cli

FIXTURES = Path(__file__).parent / "fixtures" / "k6"
SCRIPT = 'export default function () { http.get("https://h/x", { tags: { endpoint: "x" } }); }'


def test_cli_writes_suite_tasks_and_report(monkeypatch, tmp_path: Path) -> None:
    script = tmp_path / "smoke.js"
    script.write_text(SCRIPT, encoding="utf-8")
    seen: dict[str, Any] = {}

    def inspect(path: Path, env: dict[str, str]) -> dict[str, Any]:
        seen.update(path=path, env=env)
        return json.loads((FIXTURES / "smoke.inspect.json").read_text(encoding="utf-8"))

    monkeypatch.setattr(cli, "run_inspect", inspect)
    out = tmp_path / "robot"
    assert cli.main([str(script), "--out", str(out), "-e", "RUN_ID=r1", "--max-users", "5"]) == 0
    assert sorted(p.name for p in out.iterdir()) == ["smoke.report.md", "smoke.robot", "smoke_tasks.py"]
    assert seen == {"path": script, "env": {"RUN_ID": "r1"}}
    assert "users=1" in (out / "smoke.robot").read_text(encoding="utf-8")
    assert 'name=\'x\'' in (out / "smoke_tasks.py").read_text(encoding="utf-8")


def test_bad_env_pair_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        cli.main([str(tmp_path / "a.js"), "-e", "NOEQUALS"])
