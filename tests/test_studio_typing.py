"""mypy stays clean on the Studio code with and without PySide6 installed."""

import importlib.util
import os
from pathlib import Path

import pytest
from mypy import api

ROOT = Path(__file__).resolve().parent.parent
STUDIO = str(ROOT / "src" / "LocustLibrary" / "studio")
BASE = "[mypy]\npython_version = 3.11\nstrict = True\nignore_missing_imports = True\n"


def _mypy(config: Path) -> tuple[str, int]:
    before = Path.cwd()
    os.chdir(ROOT)
    try:
        out, _, status = api.run([STUDIO, "--config-file", str(config), "--no-incremental"])
    finally:
        os.chdir(before)
    return out, status


@pytest.mark.skipif(importlib.util.find_spec("PySide6") is None, reason="needs PySide6")
def test_mypy_clean_with_pyside6(tmp_path: Path) -> None:
    config = tmp_path / "mypy.ini"
    config.write_text(BASE)
    out, status = _mypy(config)
    assert status == 0, out


def test_mypy_helper_keeps_the_working_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(api, "run", lambda _args: ("", "", 0))
    _mypy(tmp_path / "mypy.ini")
    assert Path.cwd() == tmp_path


def test_mypy_clean_without_pyside6(tmp_path: Path) -> None:
    # follow_imports = skip makes PySide6 look like a missing package, as in CI.
    config = tmp_path / "mypy.ini"
    config.write_text(BASE + "\n[mypy-PySide6.*]\nfollow_imports = skip\nfollow_imports_for_stubs = True\n")
    out, status = _mypy(config)
    assert status == 0, out
