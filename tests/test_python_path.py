"""python_path lets Add Python Task find task modules without importing them as libraries."""

import sys
from pathlib import Path

import pytest

from LocustLibrary import LocustLibrary


def test_task_module_found_on_python_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "path", list(sys.path))
    (tmp_path / "pp_tasks_probe.py").write_text("def walk(user):\n    return None\n", encoding="utf-8")
    lib = LocustLibrary(python_path=str(tmp_path))
    lib.create_load_test("http://h")
    lib.add_python_task("walk", "pp_tasks_probe.walk")
    assert str(tmp_path) in sys.path


def test_no_python_path_leaves_sys_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "path", list(sys.path))
    before = list(sys.path)
    LocustLibrary()
    assert sys.path == before
