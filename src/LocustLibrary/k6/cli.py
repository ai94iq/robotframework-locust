"""rflocust-k6: convert one k6 script into a Robot project for LocustLibrary.

It reads literal options straight from the script; computed options need `k6 inspect`, which
runs the script's init code as the caller, so --trust-script is asked for then. It never runs k6 load.
Files land in the four-layer house layout; the shared entry point is rebuilt from the
collections present, and an environment file and the tasks module are written only when they do not exist yet
(--force rewrites the tasks module; --host rewrites the HOST and ALLOWED_HOSTS lines of a kept environment file).
"""

import argparse
import ast
import re
from pathlib import Path

from .emit import VARIABLES, convert, entry_point, env_variables, is_plain_host
from .options import parse_options, run_inspect
from .scan import OptionsConflict, scan_source, static_options

# The env name becomes a file name and a Robot Settings line.
_ENV_NAME = re.compile(r"[A-Za-z0-9_.-]+", re.ASCII)


def _env_name(text: str) -> str:
    if not _ENV_NAME.fullmatch(text):
        raise argparse.ArgumentTypeError(f"use letters, digits, _ . or -, got {text!r}")
    return text


def _host(text: str) -> str:
    if not is_plain_host(text):
        raise argparse.ArgumentTypeError(f"use http(s)://host[:port], got {text!r}")
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
    parser.add_argument("--host", type=_host, default=None,
                        help="HOST to write; default is the most common origin the script calls")
    parser.add_argument("--trust-script", action="store_true",
                        help="allow k6 inspect, which runs the script's init code as the caller")
    parser.add_argument("--force", action="store_true",
                        help="rewrite resources/python/<stem>_tasks.py even when it exists")
    return parser


def _write_once(path: Path, text: str) -> None:
    if not path.exists():
        path.write_text(text, encoding="utf-8")


def _set_host(path: Path, host: str) -> bool:
    """Rewrite the HOST and ALLOWED_HOSTS lines of a kept env file; False when it has neither."""
    fresh = {line.split()[0]: line for line in env_variables("dev", host).splitlines()
             if line.startswith(("${HOST}", "${ALLOWED_HOSTS}"))}
    old = path.read_text(encoding="utf-8")
    new = re.sub(r"^(\$\{(?:HOST|ALLOWED_HOSTS)\})(?:[ \t].*)?$", lambda m: fresh[m[1]], old, flags=re.MULTILINE)
    if new == old and not any(re.search(rf"^{re.escape(k)}(?:[ \t]|$)", old, flags=re.MULTILINE) for k in fresh):
        return False
    path.write_text(new, encoding="utf-8")
    return True


def _add_allow_stubs(path: Path) -> bool:
    """Append ${ALLOW_STUBS} to a kept env file that lacks it; False when it is there already."""
    old = path.read_text(encoding="utf-8")
    if re.search(r"^\$\{ALLOW_STUBS\}(?:[ \t]|$)", old, flags=re.MULTILINE):
        return False
    line = next(x for x in env_variables("dev", "").splitlines() if x.startswith("${ALLOW_STUBS}"))
    path.write_text(old + ("" if old.endswith("\n") or not old else "\n") + line + "\n", encoding="utf-8")
    return True


def _free_backup(path: Path) -> Path:
    """The first of name.bak, name.bak.1, name.bak.2 ... that does not exist; a backup is never overwritten."""
    candidate, number = path, 0
    while candidate.exists():
        number += 1
        candidate = path.with_name(f"{path.name}.{number}")
    return candidate


def _functions(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    return {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    script: Path = args.script
    if not script.is_file():
        raise SystemExit(f"rflocust-k6: no such file: {script}")
    source = script.read_text(encoding="utf-8")
    try:
        data, row = static_options(source), "| options | read statically |\n"
    except OptionsConflict as err:
        raise SystemExit(f"rflocust-k6: {err}; k6 refuses this script too, so fix its options") from None
    except ValueError as err:
        if not args.trust_script:
            raise SystemExit(f"rflocust-k6: {err}, so k6 inspect is needed; k6 inspect runs the script's "
                             "init code as the caller; pass --trust-script to convert a script you trust") from None
        data, row = run_inspect(script, dict(args.env)), f"| options | from k6 inspect | {err} |\n"
    done = convert(script.name, parse_options(data), scan_source(source), args.max_users, args.host)
    out: Path = args.out
    files = dict(done.files)
    files[f"reports/{script.stem}.k6-report.md"] += row
    tasks = f"resources/python/{script.stem}_tasks.py"
    if (out / tasks).exists() and not args.force:
        wanted = _functions(files.pop(tasks))
        report = f"reports/{script.stem}.k6-report.md"
        files[report] += f"| tasks file | kept | {tasks} exists; pass --force to rewrite it |\n"
        missing = sorted(wanted - _functions((out / tasks).read_text(encoding="utf-8")))
        if missing:
            files[report] += (f"| tasks file | missing | {', '.join(missing)} | the suite calls "
                              "these but the kept file does not define them |\n")
    elif (out / tasks).exists() and (old := (out / tasks).read_text(encoding="utf-8")) != files[tasks]:
        backup = _free_backup(out / f"{tasks}.bak")
        backup.write_text(old, encoding="utf-8")
        files[f"reports/{script.stem}.k6-report.md"] += (
            f"| tasks file | backed up | old {tasks} copied to {backup.relative_to(out).as_posix()} "
            "before the rewrite |\n")
    env_file = out / "resources" / f"{args.env_name}_variables.resource"
    if args.host is not None and env_file.exists() and not _set_host(env_file, done.host):
        files[f"reports/{script.stem}.k6-report.md"] += (
            f"| host | not applied | resources/{env_file.name} has no ${{HOST}} or ${{ALLOWED_HOSTS}} line; "
            "set them there by hand |\n")
    if env_file.exists() and _add_allow_stubs(env_file):
        files[f"reports/{script.stem}.k6-report.md"] += (
            f"| env file | updated | resources/{env_file.name} had no ${{ALLOW_STUBS}}; added it as ${{False}} |\n")
    for relative, text in files.items():
        (out / relative).parent.mkdir(parents=True, exist_ok=True)
        (out / relative).write_text(text, encoding="utf-8")
    collections = sorted(p.name for p in (out / "collections").glob("*_test_keywords.resource"))
    (out / "resources" / "resources.resource").write_text(entry_point(collections), encoding="utf-8")
    _write_once(out / "resources" / "variables.resource", VARIABLES)
    _write_once(env_file, env_variables(args.env_name, done.host))
    print(f"wrote {len(done.files)} files for {script.name} to {out}")
    return 0
