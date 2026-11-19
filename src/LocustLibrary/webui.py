"""Web UI mode wrapper."""

import subprocess
import sys


def start_web_ui(
    locustfile: str, port: int = 8089, host: str = "127.0.0.1"
) -> subprocess.Popen[bytes]:
    """Start Locust web UI as a subprocess. Returns the process handle."""
    from .validation import validate_locustfile

    locustfile = validate_locustfile(locustfile)
    cmd = [sys.executable, "-m", "locust", "-f", locustfile, "--web-host", host,
           "--web-port", str(port)]
    return subprocess.Popen(cmd)


def stop_web_ui(proc: subprocess.Popen[bytes]) -> None:
    """Stop a web UI process."""
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
