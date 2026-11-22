"""Distributed worker support."""

import subprocess
import sys

from .validation import validate_locustfile

# Locust binds every interface when these flags are left off.
_LOOPBACK = "127.0.0.1"


def run_distributed(
    locustfile: str, processes: int = 2, master_port: int = 5557,
    extra: list[str] | None = None,
) -> tuple[subprocess.Popen[bytes], list[subprocess.Popen[bytes]]]:
    """Run Locust in distributed mode (master + workers)."""
    locustfile = validate_locustfile(locustfile)
    master = subprocess.Popen([
        sys.executable, "-m", "locust", "-f", locustfile, "--master",
        "--master-bind-host", _LOOPBACK,
        "--master-bind-port", str(master_port),
        "--web-host", _LOOPBACK, *(extra or []),
    ])
    workers: list[subprocess.Popen[bytes]] = []
    for _ in range(processes):
        workers.append(subprocess.Popen([
            sys.executable, "-m", "locust", "-f", locustfile, "--worker",
            "--master-host", _LOOPBACK, "--master-port", str(master_port),
        ]))
    return master, workers


def stop_distributed(
    master: subprocess.Popen[bytes] | None,
    workers: list[subprocess.Popen[bytes]] | None,
) -> None:
    """Stop a master and its workers started by run_distributed."""
    procs: list[subprocess.Popen[bytes]] = []
    if master is not None:
        procs.append(master)
    procs.extend(workers or [])
    for proc in procs:
        _stop_one(proc)


def _stop_one(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
