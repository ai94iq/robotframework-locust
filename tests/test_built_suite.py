"""The Build tab's tasks become a Robot suite that runs through the same path as an opened suite."""

import io
from pathlib import Path

import pytest
import robot

from LocustLibrary.studio.built_suite import suite_text, write_suite

SCENARIO = {"host": "http://127.0.0.1:8765", "wait_min": "0.1s", "wait_max": "0.5s",
            "tasks": [{"name": "Get Home", "method": "GET", "path": "/", "weight": 2},
                      {"name": "Send Order", "method": "POST", "path": "/orders", "weight": 1}]}
RUN = {"users": 5, "spawn_rate": 2.0, "run_time": "20s"}


def test_suite_lists_every_step() -> None:
    """Every task, the default guards, the run values and the report export are in the suite."""
    steps = [line.strip() for line in suite_text(SCENARIO, RUN).splitlines() if line.startswith("    ")]
    assert steps == [
        "Create Load Test    http://127.0.0.1:8765",
        "Set Wait Time    0.1s    0.5s",
        "Add Get Request    Get Home    /    weight=2",
        "Add Post Request    Send Order    /orders    weight=1",
        "Add Stop Rule    fail > 10% for 30s",
        "Add Stop Rule    idle > 30s",
        "Run Load Test    users=5    spawn_rate=2.0    run_time=20s    stop_on_fail_ratio=20%",
        "Export Report",
    ]


@pytest.mark.parametrize("name", ["a  b", "a\tb", "a\nb", " a", "a ", ""])
def test_unsafe_value_is_refused(name: str) -> None:
    """A value that would split into more Robot cells or lines is refused, not written."""
    tasks = [{**SCENARIO["tasks"][0], "name": name}]
    with pytest.raises(ValueError, match="one suite value"):
        suite_text({**SCENARIO, "tasks": tasks}, RUN)


def test_robot_syntax_is_escaped() -> None:
    """Equals signs, a leading hash and variable syntax stay plain text."""
    tasks = [{**SCENARIO["tasks"][0], "name": "#a=b ${x}"}]
    assert "Add Get Request    \\#a\\=b \\${x}    /" in suite_text({**SCENARIO, "tasks": tasks}, RUN)


def test_built_suite_passes_dryrun(tmp_path: Path) -> None:
    """The written suite is valid Robot: a dry run resolves every keyword."""
    path = write_suite(SCENARIO, RUN, tmp_path / "built.robot")
    code = robot.run(str(path), dryrun=True, output=None, report=None, log=None, stdout=io.StringIO())
    assert code == 0
