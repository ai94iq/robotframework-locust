"""Input validation helpers for LocustLibrary."""

import os
from pathlib import Path
from urllib.parse import urlsplit


def validate_host(host: str) -> str:
    host = (host or "").strip()
    parts = urlsplit(host)
    if parts.scheme not in {"http", "https"} or parts.hostname is None:
        raise ValueError("host must be an http or https URL")
    if parts.username is not None or parts.password is not None:
        raise ValueError("host must not include credentials")
    return host


def validate_locustfile(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        raise ValueError(f"locustfile not found: {path}")
    return str(p.resolve())


def sanitize_prefix(name: str) -> str:
    name = (name or "locust").strip()
    # keep basename only
    name = os.path.basename(name)
    if not name or name in (".", ".."):
        name = "locust"
    # remove path separators
    name = name.replace("/", "").replace("\\", "")
    if not name:
        name = "locust"
    return name


def validate_output_path(base: str, output_dir: str | None = None) -> str:
    base = sanitize_prefix(base)
    root = Path(output_dir) if output_dir else Path.cwd()
    root = root.resolve()
    target = (root / base).resolve()
    if root not in target.parents and target != root:
        raise ValueError("output path escapes output directory")
    return str(target)
