"""Endpoint checks see every method under a name; k6 inspect gets a small env."""

import subprocess
from pathlib import Path
from typing import Any

import pytest

from LocustLibrary import LocustLibrary
from LocustLibrary.k6 import emit, options
from LocustLibrary.scenario import Stats, StatsRow


def _lib_with_get_and_post() -> LocustLibrary:
    lib = LocustLibrary()
    get = StatsRow("/items", request_count=10, p95=100.0)
    post = StatsRow("/items", request_count=10, failure_count=5, p95=900.0)
    lib._stats = Stats(rows=[get, post], aggregated=StatsRow("Aggregated", request_count=20))
    return lib


def test_error_rate_counts_every_method() -> None:
    with pytest.raises(AssertionError, match="25.00%"):
        _lib_with_get_and_post().should_meet_error_rate("5%", "/items")


def test_response_time_checks_every_method() -> None:
    with pytest.raises(AssertionError, match="900"):
        _lib_with_get_and_post().should_meet_response_time("/items", "p95", "500ms")


def test_inspect_gets_no_ambient_secrets(monkeypatch: Any, tmp_path: Path) -> None:
    seen: dict[str, Any] = {}

    def run(args: list[str], **kwargs: Any) -> Any:
        seen.update(kwargs)
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setenv("DUMMY_TOKEN", "secret")
    monkeypatch.setattr(options.shutil, "which", lambda _name: "/bin/k6")
    monkeypatch.setattr(options.subprocess, "run", run)
    options.run_inspect(tmp_path / "a.js", {})
    assert "DUMMY_TOKEN" not in seen["env"]
    assert "PATH" in seen["env"]


def test_double_underscore_title_has_one_space() -> None:
    done = emit.convert("a__b.js", options.K6Options((), (), False, 0.0, 1), [])
    assert "Test A B Load\n" in done.files["tests/a__b.robot"]


@pytest.mark.parametrize("name", ["a b.js", 'x"y.js', "a\nb.js"])
def test_odd_script_name_is_refused(name: str) -> None:
    with pytest.raises(ValueError, match="script name"):
        emit.convert(name, options.K6Options((), (), False, 0.0, 1), [])
