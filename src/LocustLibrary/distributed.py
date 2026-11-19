"""Distributed worker support."""

import subprocess
import sys


def run_distributed(locustfile: str, processes: int = 2, master_port: int = 5557) -> None:
    """Run Locust in distributed mode (master + workers)."""
    master = subprocess.Popen([
        sys.executable, "-m", "locust", "-f", locustfile, "--master",
        "--master-bind-port", str(master_port),
    ])
    workers = []
    for _ in range(processes):
        workers.append(subprocess.Popen([
            sys.executable, "-m", "locust", "-f", locustfile, "--worker",
            "--master-host", "127.0.0.1", "--master-port", str(master_port),
        ]))
    return master, workers
