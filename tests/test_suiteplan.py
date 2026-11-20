"""Studio reads a load suite's classes and tasks the way Robot resolves them."""

from pathlib import Path

from LocustLibrary.suiteplan import read_suite

SUITE = """*** Settings ***
Library    LocustLibrary

*** Test Cases ***
Load
    Build Users
    Run Load Test    users=1    run_time=1s

*** Keywords ***
Build Users
    Create Load Test    http://127.0.0.1:9    verify_tls=${False}
    Add User Class    signup    fixed_count=4
    Set Wait Time    5s    5s
    Add Python Task    signupScenario    tasks.signup
    Add User Class    token    weight=3
    Add Get Request    home    /
"""


def test_classes_and_tasks_come_from_the_keywords(tmp_path: Path) -> None:
    suite = tmp_path / "load.robot"
    suite.write_text(SUITE, encoding="utf-8")
    plan = read_suite(str(suite))
    assert plan.host == "http://127.0.0.1:9"
    assert [(c.name, c.size, c.wait) for c in plan.classes] == [
        ("signup", "fixed_count=4", "5s - 5s"), ("token", "weight=3", "")]
    assert plan.classes[0].tasks == ["Add Python Task: signupScenario"]
    assert plan.classes[1].tasks == ["Add Get Request: home"]


def test_tasks_before_a_class_go_to_the_default(tmp_path: Path) -> None:
    suite = tmp_path / "plain.robot"
    suite.write_text(SUITE.replace("    Add User Class    signup    fixed_count=4\n", ""), encoding="utf-8")
    plan = read_suite(str(suite))
    assert plan.classes[0].name == "RFUser"
    assert plan.classes[0].tasks == ["Add Python Task: signupScenario"]


def test_host_from_a_resource_is_resolved(tmp_path: Path) -> None:
    (tmp_path / "vars.resource").write_text(
        "*** Variables ***\n${HOST}    http://127.0.0.1:9\n", encoding="utf-8")
    suite = tmp_path / "load.robot"
    suite.write_text(SUITE.replace("Library    LocustLibrary\n",
                                   "Library    LocustLibrary\nResource    vars.resource\n")
                     .replace("http://127.0.0.1:9", "${HOST}", 1), encoding="utf-8")
    assert read_suite(str(suite)).host == "http://127.0.0.1:9"


def test_an_unknown_variable_stays_as_written(tmp_path: Path) -> None:
    suite = tmp_path / "load.robot"
    suite.write_text(SUITE.replace("http://127.0.0.1:9", "${NOPE}", 1), encoding="utf-8")
    assert read_suite(str(suite)).host == "${NOPE}"


def test_a_suite_without_load_keywords_is_empty(tmp_path: Path) -> None:
    suite = tmp_path / "none.robot"
    suite.write_text("*** Test Cases ***\nA\n    Log    hi\n", encoding="utf-8")
    plan = read_suite(str(suite))
    assert (plan.host, plan.classes) == ("", [])
