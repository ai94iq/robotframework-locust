"""Distributed worker support."""

import subprocess
import sys

from .validation import validate_locustfile


def run_distributed(locustfile: str, processes: int = 2, master_port: int = 5557):
    """Run Locust in distributed mode (master + workers)."""
    locustfile = validate_locustfile(locustfile)
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
