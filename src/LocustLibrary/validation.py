"""Input validation helpers for LocustLibrary."""

import os
from pathlib import Path
from urllib.parse import urlsplit

ALLOWED_HOSTS_ENV = "LOCUSTLIBRARY_ALLOWED_HOSTS"


def allowed_hosts(value: str) -> list[str]:
    """Host names from the argument, else from LOCUSTLIBRARY_ALLOWED_HOSTS; comma separated."""
    raw = value or os.environ.get(ALLOWED_HOSTS_ENV, "")
    return [name.strip().lower() for name in raw.split(",") if name.strip()]


def validate_host(host: str, allowed: list[str] | None = None) -> str:
    host = (host or "").strip()
    parts = urlsplit(host)
    if parts.scheme not in {"http", "https"} or parts.hostname is None:
        raise ValueError("host must be an http or https URL")
    if parts.username is not None or parts.password is not None:
        raise ValueError("host must not include credentials")
    if allowed and parts.hostname.lower() not in allowed:
        raise ValueError(f"{parts.hostname} is not in the allowed hosts: {', '.join(allowed)}")
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
