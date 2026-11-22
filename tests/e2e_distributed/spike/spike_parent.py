"""Stand-in Robot process: starts one idle spike child, prints its pid, then waits."""
import os
import subprocess
import sys
import time
from pathlib import Path

NODE = Path(__file__).with_name("spike_node.py")


def main() -> None:
    """Start the child in a new process group at low priority and wait to be killed."""
    extra = sys.argv[1:]
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.BELOW_NORMAL_PRIORITY_CLASS
    env = {**os.environ, "LOCUSTLIBRARY_PARENT_PID": str(os.getpid())}
    child = subprocess.Popen([sys.executable, str(NODE), "idle", *extra], creationflags=flags, env=env)
    print(os.getpid(), child.pid, flush=True)
    time.sleep(600)


if __name__ == "__main__":
    main()
