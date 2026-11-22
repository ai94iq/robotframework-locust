"""Start and end spike processes for the S1 tests."""
import json
import os
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import psutil

NODE = Path(__file__).with_name("spike_node.py")
PARENT = Path(__file__).with_name("spike_parent.py")
LOW = subprocess.BELOW_NORMAL_PRIORITY_CLASS if sys.platform == "win32" else 0


def free_port() -> int:
    """A free loopback TCP port for the master."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def start(args: list[str], **kwargs: Any) -> subprocess.Popen[str]:
    """One spike node at low priority."""
    return subprocess.Popen([sys.executable, str(NODE), *args], creationflags=LOW, text=True, **kwargs)


def end(procs: list[subprocess.Popen[str]]) -> None:
    """Kill every process that is still running."""
    for proc in procs:
        if proc.poll() is None:
            proc.kill()
            proc.wait(10)


def run_cluster(workers: int, interval: float, extra: list[str]) -> dict[str, Any]:
    """Run one master and its workers to the end; return the master's JSON."""
    port = free_port()
    master = start(["master", "--port", str(port), "--workers", str(workers), *extra],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    nodes = [master] + [start(["worker", "--port", str(port), "--id", str(i), "--interval", str(interval)])
                        for i in range(workers)]
    try:
        stdout, stderr = master.communicate(timeout=180)
    finally:
        end(nodes)
    return {**json.loads(stdout.strip().splitlines()[-1]), "master_log": stderr.splitlines()[-40:]}


def save(name: str, data: dict[str, Any]) -> None:
    """Write a result to RFL_SPIKE_OUT when it is set."""
    folder = os.environ.get("RFL_SPIKE_OUT")
    if folder:
        Path(folder).mkdir(parents=True, exist_ok=True)
        Path(folder, f"{name}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


def real_python(launched: psutil.Process) -> psutil.Process:
    """The python that runs the code: the launcher's child on a Windows venv, else itself."""
    for _ in range(50):
        if launched.children():
            return launched.children()[0]
        if sys.platform != "win32":
            return launched
        psutil.wait_procs([launched], timeout=0.1)
    return launched


def orphan_after(seconds: float, extra: list[str], suspend: bool) -> dict[str, Any]:
    """Kill the stand-in Robot python, optionally with its worker suspended; report if the worker lives."""
    launcher = subprocess.Popen([sys.executable, str(PARENT), *extra], stdout=subprocess.PIPE, text=True)
    assert launcher.stdout is not None
    parent_pid, child_pid = map(int, launcher.stdout.readline().split())
    child = real_python(psutil.Process(child_pid))
    assert launcher.stdout.readline().strip() == "ready"
    if suspend:
        child.suspend()
    psutil.Process(parent_pid).kill()
    gone, _ = psutil.wait_procs([child], timeout=seconds)
    alive = not gone
    end([launcher])
    if alive:
        child.kill()
    return {"suspended": suspend, "waited_s": seconds, "child_alive": alive, "platform": sys.platform}
