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


def test_pacing_and_stop_rules_are_listed(tmp_path: Path) -> None:
    suite = tmp_path / "paced.robot"
    suite.write_text(SUITE.replace("    Set Wait Time    5s    5s\n",
                                   "    Set Pacing    2s\n    Add Stop Rule    p95 > 1s for 10s\n"),
                     encoding="utf-8")
    plan = read_suite(str(suite))
    assert (plan.classes[0].pacing, plan.classes[0].wait) == ("2s", "")
    assert plan.stop_rules == ["p95 > 1s for 10s"]


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


def test_libraries_and_variable_files_are_never_imported(tmp_path: Path) -> None:
    marker = tmp_path / "imported.txt"
    (tmp_path / "evil.py").write_text(
        f"open({str(marker)!r}, 'a').write('x')\nHOST = 'http://evil'\n", encoding="utf-8")
    suite = tmp_path / "load.robot"
    suite.write_text(SUITE.replace("Library    LocustLibrary\n",
                                   "Library    LocustLibrary\nLibrary    evil.py\nVariables    evil.py\n"),
                     encoding="utf-8")
    plan = read_suite(str(suite))
    assert not marker.exists()
    assert plan.host == "http://127.0.0.1:9"


def test_nested_resources_loops_and_recursion_are_followed(tmp_path: Path) -> None:
    (tmp_path / "inner.resource").write_text(
        "*** Variables ***\n${HOST}    http://127.0.0.1:9\n", encoding="utf-8")
    (tmp_path / "outer.resource").write_text(
        "*** Settings ***\nResource    inner.resource\nResource    missing.resource\n"
        "Resource    outer.resource\n\n*** Keywords ***\nAgain\n    Again\n", encoding="utf-8")
    suite = tmp_path / "load.robot"
    suite.write_text(
        "*** Settings ***\nLibrary    LocustLibrary\nResource    outer.resource\n\n"
        "*** Test Cases ***\nLoad\n    Again\n    FOR    ${i}    IN    a\n"
        "        LocustLibrary.Create Load Test    ${HOST}\n    END\n", encoding="utf-8")
    assert read_suite(str(suite)).host == "http://127.0.0.1:9"


def test_sibling_suites_keep_their_own_keywords_and_variables(tmp_path: Path) -> None:
    (tmp_path / "a.robot").write_text(
        "*** Variables ***\n${NAME}    from_a\n\n*** Test Cases ***\nLoad\n    Build\n\n"
        "*** Keywords ***\nBuild\n    LocustLibrary.Add User Class    ${NAME}\n", encoding="utf-8")
    (tmp_path / "b.robot").write_text(
        "*** Test Cases ***\nLoad\n    Build\n\n"
        "*** Keywords ***\nBuild\n    LocustLibrary.Add User Class    ${NAME}_b\n", encoding="utf-8")
    assert [c.name for c in read_suite(str(tmp_path)).classes] == ["from_a", "${NAME}_b"]


def test_keyword_arguments_are_bound(tmp_path: Path) -> None:
    suite = tmp_path / "load.robot"
    suite.write_text(
        "*** Variables ***\n${TARGET}    http://127.0.0.1:7\n\n*** Test Cases ***\nLoad\n"
        "    Start    ${TARGET}    cls=web\n    Start    http://x\n\n*** Keywords ***\nStart\n"
        "    [Arguments]    ${host}    ${cls}=api    @{rest}\n    LocustLibrary.Create Load Test    ${host}\n"
        "    LocustLibrary.Add User Class    ${cls}\n", encoding="utf-8")
    plan = read_suite(str(suite))
    assert [c.name for c in plan.classes] == ["web", "api"]
    assert plan.host == "http://x"


def test_a_directory_reads_every_child_suite(tmp_path: Path) -> None:
    (tmp_path / "a.robot").write_text(SUITE, encoding="utf-8")
    assert len(read_suite(str(tmp_path)).classes) == 2
