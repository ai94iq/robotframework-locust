"""rflocust-k6: convert one k6 script into a Robot suite for LocustLibrary.

It reads options through `k6 inspect` (init code only, no requests) and never runs k6 load.
"""

import argparse
from pathlib import Path

from .emit import convert
from .options import parse_options, run_inspect
from .scan import scan_source


def _env_pair(text: str) -> tuple[str, str]:
    key, sep, value = text.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"use KEY=VALUE, got {text!r}")
    return key, value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rflocust-k6", description=__doc__)
    parser.add_argument("script", type=Path, help="k6 entry script")
    parser.add_argument("--out", type=Path, default=Path("robot"), help="output folder")
    parser.add_argument("-e", dest="env", type=_env_pair, action="append", default=[],
                        help="k6 -e KEY=VALUE passed to k6 inspect")
    parser.add_argument("--max-users", type=int, default=100, help="user ceiling, default 100")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    script: Path = args.script
    opts = parse_options(run_inspect(script, dict(args.env)))
    functions = scan_source(script.read_text(encoding="utf-8"))
    done = convert(script.name, opts, functions, args.max_users)
    args.out.mkdir(parents=True, exist_ok=True)
    stem = script.stem
    (args.out / f"{stem}.robot").write_text(done.robot, encoding="utf-8")
    (args.out / f"{stem}_tasks.py").write_text(done.tasks, encoding="utf-8")
    (args.out / f"{stem}.report.md").write_text(done.report, encoding="utf-8")
    print(f"wrote {stem}.robot, {stem}_tasks.py and {stem}.report.md to {args.out}")
    return 0
