"""Spike node: one Locust master, worker or idle child for the S1 measurements."""
from gevent import monkey

monkey.patch_all()

import argparse
import ctypes
import json
import os
import statistics
import sys
import time
from typing import Any

import gevent
import psutil

PR_SET_PDEATHSIG = 1
SIGKILL = 9


def fire_sample(user: Any, name: str) -> None:
    """Record one fake request so stats reports carry rows."""
    user.environment.events.request.fire(
        request_type="SPIKE", name=name, response_time=1, response_length=0, exception=None, context={})


def user_classes() -> list[type]:
    """One fixed_count class and one weighted class, both without network calls."""
    from locust import User, constant, task

    class Fixed(User):
        fixed_count = 3
        wait_time = constant(0.05)

        @task
        def work(self) -> None:
            fire_sample(self, "fixed")

    class Weighted(User):
        wait_time = constant(0.05)

        @task
        def work(self) -> None:
            fire_sample(self, "weighted")

    return [Fixed, Weighted]


def add_report_extra(env: Any, state: dict[str, Any]) -> None:
    """Put a sequence number and the final flag into every stats report (M5)."""
    def on_report(client_id: str, data: dict[str, Any]) -> None:
        state["seq"] += 1
        data["rfl"] = {"seq": state["seq"], "final": state["final"]}
    env.events.report_to_master.add_listener(on_report)


def add_final_report(env: Any, runner: Any, state: dict[str, Any]) -> None:
    """On test_stop send one stats report marked final (design section 0, D2)."""
    def on_stop(**_: Any) -> None:
        state["final"] = True
        runner._send_stats()
        state["final"] = False
    env.events.test_stop.add_listener(on_stop)


def run_worker(args: argparse.Namespace) -> None:
    """Connect a WorkerRunner to the master and answer the ping with an ack."""
    import locust.runners
    from locust.env import Environment

    locust.runners.WORKER_REPORT_INTERVAL = args.interval
    env = Environment(user_classes=user_classes())
    runner = env.create_worker_runner("127.0.0.1", args.port)
    state: dict[str, Any] = {"seq": 0, "final": False}
    add_report_extra(env, state)
    add_final_report(env, runner, state)
    runner.register_message("rfl_pong", lambda msg, **_: runner.send_message("rfl_ack", msg.data))
    runner.send_message("rfl_ping", {"worker": args.id})
    runner.greenlet.join()


def record_arrivals(runner: Any, arrivals: list[dict[str, Any]]) -> None:
    """Log every message the master receives, in arrival order."""
    receive = runner.server.recv_from_client

    def logged() -> Any:
        client_id, msg = receive()
        final = msg.data.get("rfl", {}).get("final") if isinstance(msg.data, dict) else None
        arrivals.append({"type": msg.type, "node": msg.node_id, "final": final, "t": time.monotonic()})
        return client_id, msg
    runner.server.recv_from_client = logged


def add_master_messages(runner: Any, out: dict[str, Any]) -> None:
    """Answer each ping with a pong to that worker; keep acks and report extras."""
    out.update(acks={}, extras=[])
    runner.register_message(
        "rfl_ping", lambda msg, **_: runner.send_message("rfl_pong", msg.data, client_id=msg.node_id))
    runner.register_message("rfl_ack", lambda msg, **_: out["acks"].__setitem__(msg.node_id, msg.data))
    runner.environment.events.worker_report.add_listener(
        lambda client_id, data: out["extras"].append({"node": client_id, **data.get("rfl", {})}))


def tick_periods(periods: list[float]) -> None:
    """Sleep 0.5 s in a loop and keep each real period, like the guard tick."""
    last = time.monotonic()
    while True:
        gevent.sleep(0.5)
        now = time.monotonic()
        periods.append(now - last)
        last = now


def wait_for_workers(runner: Any, count: int) -> None:
    """Block until the master has count ready workers, at most 60 s."""
    with gevent.Timeout(60):
        while runner.worker_count < count:
            gevent.sleep(0.1)


def hub_cost(cpu_before: float, wall: float, periods: list[float], window: list[dict[str, Any]]) -> dict[str, float]:
    """CPU share of one core, tick p95, all messages and stats reports per second over the window."""
    cpu = sum(psutil.Process().cpu_times()[:2]) - cpu_before
    p95 = statistics.quantiles(periods, n=20)[-1] if len(periods) > 1 else 0.0
    return {"cpu_share": cpu / wall, "tick_p95": p95, "tick_max": max(periods, default=0.0),
            "msgs_per_s": len(window) / wall, "stats_per_s": sum(a["type"] == "stats" for a in window) / wall,
            "ticks": len(periods), "wall": wall}


def measure_load(runner: Any, args: argparse.Namespace, out: dict[str, Any]) -> None:
    """Run the load window and store user counts and the hub cost."""
    periods: list[float] = []
    ticker = gevent.spawn(tick_periods, periods)
    runner.start(args.users, spawn_rate=args.users)
    gevent.sleep(args.warmup)
    seen = len(out["arrivals"])
    cpu_before, start = sum(psutil.Process().cpu_times()[:2]), time.monotonic()
    periods.clear()
    gevent.sleep(args.duration)
    out["hub"] = hub_cost(cpu_before, time.monotonic() - start, periods, out["arrivals"][seen:])
    ticker.kill()
    out["per_class"] = dict(runner.reported_user_classes_count)
    out["per_worker"] = {cid: dict(node.user_classes_count) for cid, node in runner.clients.items()}


def run_master(args: argparse.Namespace) -> None:
    """Run master, load, stop and quit; print one JSON line with what was seen."""
    from locust.env import Environment

    env = Environment(user_classes=user_classes())
    runner = env.create_master_runner("127.0.0.1", args.port)
    out: dict[str, Any] = {"arrivals": []}
    record_arrivals(runner, out["arrivals"])
    add_master_messages(runner, out)
    wait_for_workers(runner, args.workers)
    measure_load(runner, args, out)
    out["stop_mark"] = time.monotonic()
    runner.stop()
    out["quit_mark"] = time.monotonic()
    runner.quit()
    gevent.sleep(0.5)
    print(json.dumps(out), flush=True)


def set_pdeathsig() -> None:
    """Ask the Linux kernel to SIGKILL this process when its parent thread ends."""
    libc = ctypes.CDLL("libc.so.6", use_errno=True)
    if libc.prctl(PR_SET_PDEATHSIG, SIGKILL) != 0:
        raise OSError(ctypes.get_errno(), "prctl failed")


def watch_parent(pid: int) -> None:
    """Exit when the parent process is gone (parent watch, R31)."""
    while psutil.pid_exists(pid):
        gevent.sleep(1)
    os._exit(3)


def run_idle(args: argparse.Namespace) -> None:
    """Orphan probe: optional pdeathsig, parent watch, then sleep."""
    if args.pdeathsig:
        set_pdeathsig()
    gevent.spawn(watch_parent, int(os.environ["LOCUSTLIBRARY_PARENT_PID"]))
    print("ready", flush=True)
    gevent.sleep(600)


def parse(argv: list[str]) -> argparse.Namespace:
    """Read the role and its numbers from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=["master", "worker", "idle"])
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--users", type=int, default=10)
    parser.add_argument("--warmup", type=float, default=3.0)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--interval", type=float, default=3.0)
    parser.add_argument("--pdeathsig", action="store_true")
    return parser.parse_args(argv)


if __name__ == "__main__":
    parsed = parse(sys.argv[1:])
    {"master": run_master, "worker": run_worker, "idle": run_idle}[parsed.role](parsed)
