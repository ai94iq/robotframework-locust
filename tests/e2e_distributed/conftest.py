"""Real-process tests run only when RFL_E2E=1 is set."""
import os

collect_ignore_glob = [] if os.environ.get("RFL_E2E") == "1" else ["*"]
