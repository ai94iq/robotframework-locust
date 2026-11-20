"""rflocust-k6: convert one k6 script into a Robot project for LocustLibrary.

It reads options through `k6 inspect`, which runs the script's init code as the caller, so
convert only trusted scripts. It never runs k6 load.
Files land in the four-layer house layout; the shared entry point is rebuilt from the
collections present, and an environment file is written only when it does not exist yet.
"""

import argparse
import re
from pathlib import Path

from .emit import VARIABLES, convert, entry_point, env_variables
from .options import parse_options, run_inspect
from .scan import scan_source

# The env name becomes a file name and a Robot Settings line.
_ENV_NAME = re.compile(r"[A-Za-z0-9_.-]+", re.ASCII)


def _env_name(text: str) -> str:
    if not _ENV_NAME.fullmatch(text):
        raise argparse.ArgumentTypeError(f"use letters, digits, _ . or -, got {text!r}")
    return text


def _env_pair(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"use KEY=VALUE, got {text!r}")
    return key, value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rflocust-k6", description=__doc__)
    parser.add_argument("script", type=Path, help="k6 entry script")
    parser.add_argument("--out", type=Path, default=Path("robot"), help="project folder")
    parser.add_argument("-e", dest="env", type=_env_pair, action="append", default=[],
                        help="k6 -e KEY=VALUE passed to k6 inspect")
    parser.add_argument("--max-users", type=int, default=100, help="user ceiling, default 100")
    parser.add_argument("--env-name", type=_env_name, default="dev", help="environment file to create, default dev")
    return parser


def _write_once(path: Path, text: str) -> None:
    if not path.exists():
        path.write_text(text, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    script: Path = args.script
    opts = parse_options(run_inspect(script, dict(args.env)))
    done = convert(script.name, opts, scan_source(script.read_text(encoding="utf-8")),
                   args.max_users)
    out: Path = args.out
    for relative, text in done.files.items():
        (out / relative).parent.mkdir(parents=True, exist_ok=True)
        (out / relative).write_text(text, encoding="utf-8")
    collections = sorted(p.name for p in (out / "collections").glob("*_test_keywords.resource"))
    (out / "resources" / "resources.resource").write_text(entry_point(collections), encoding="utf-8")
    _write_once(out / "resources" / "variables.resource", VARIABLES)
    _write_once(out / "resources" / f"{args.env_name}_variables.resource",
                env_variables(args.env_name, done.host))
    print(f"wrote {len(done.files)} files for {script.name} to {out}")
    return 0
