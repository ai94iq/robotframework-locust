"""S1 spike (design section 6, phase 0): Locust master and workers as real processes."""
import sys
from typing import Any

import pytest
from cluster import orphan_after, run_cluster, save

WORKERS = 4
USERS = 40
LOAD = ["--users", str(USERS), "--duration", "20"]


@pytest.fixture(scope="module")
def run3() -> dict[str, Any]:
    """One 4-worker run at the default 3 s report interval."""
    result = run_cluster(WORKERS, 3.0, LOAD)
    save("run_interval_3s", result)
    return result


def nodes(run: dict[str, Any]) -> set[str]:
    """Worker ids the master saw."""
    return {a["node"] for a in run["arrivals"] if a["type"] == "client_ready"}


def test_register_message_round_trip(run3: dict[str, Any]) -> None:
    """S1-1: ping to master, pong to that worker, ack back, for every worker."""
    echoed = sorted(ack["worker"] for ack in run3["acks"].values())
    assert echoed == list(range(WORKERS))


def test_report_extra_reaches_master(run3: dict[str, Any]) -> None:
    """S1-2: data added in report_to_master arrives in worker_report on the master."""
    reporters = {e["node"] for e in run3["extras"] if e.get("seq")}
    assert reporters == nodes(run3)


def test_fixed_count_is_run_wide(run3: dict[str, Any]) -> None:
    """S1-3: fixed_count 3 means 3 users over all workers, not 3 per worker."""
    assert run3["per_class"] == {"Fixed": 3, "Weighted": USERS - 3}


def first_index(arrivals: list[dict[str, Any]], node: str, kind: str, final: bool | None) -> int:
    """Index of the first message of one kind from one node, -1 when none."""
    for index, a in enumerate(arrivals):
        if a["node"] == node and a["type"] == kind and (final is None or a["final"] is final):
            return index
    return -1


def test_final_report_before_stopped(run3: dict[str, Any]) -> None:
    """S1-4: the final report from test_stop arrives before client_stopped, per worker."""
    arrivals = run3["arrivals"]
    order = {n: (first_index(arrivals, n, "stats", True), first_index(arrivals, n, "client_stopped", None))
             for n in nodes(run3)}
    assert all(0 <= final < stopped for final, stopped in order.values()), order


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="parent-death signal is Linux only")
def test_linux_pdeathsig_kills_suspended() -> None:
    """S1-5: a suspended worker with the parent-death signal dies with its parent."""
    result = orphan_after(10, ["--pdeathsig"], suspend=True)
    save("orphan_linux_suspended", result)
    assert result["child_alive"] is False


@pytest.mark.skipif(sys.platform != "win32", reason="measures the Windows gap")
def test_windows_suspended_orphan_gap() -> None:
    """S1-6: parent watch ends a running orphan; a suspended one outlives 10 s (the gap)."""
    running = orphan_after(10, [], suspend=False)
    suspended = orphan_after(12, [], suspend=True)
    save("orphan_windows", {"running": running, "suspended": suspended})
    assert (running["child_alive"], suspended["child_alive"]) == (False, True)


def test_hub_cost_1s_vs_3s(run3: dict[str, Any]) -> None:
    """S1-7: the 1 s interval sends about 3 times the stats reports; both costs are saved."""
    run1 = run_cluster(WORKERS, 1.0, LOAD)
    save("run_interval_1s", run1)
    save("hub_cost", {"interval_1s": run1["hub"], "interval_3s": run3["hub"]})
    assert run1["hub"]["stats_per_s"] > 2 * run3["hub"]["stats_per_s"]
