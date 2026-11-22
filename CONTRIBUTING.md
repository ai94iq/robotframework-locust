# Contributing

Thanks for helping. Bug reports, fixes and new keywords are all welcome.

## Contents

- [Report a bug](#report-a-bug)
- [Set up](#set-up)
- [Checks](#checks)
- [Rules for a change](#rules-for-a-change)
- [Tests](#tests)
- [Commits and merge requests](#commits-and-merge-requests)
- [Security](#security)
- [k6 converter internals](#k6-converter-internals)
- [Research sources](#research-sources)

## Report a bug

Open an issue with:

- the suite or the smallest part of it that shows the bug,
- the Robot log or console output,
- your versions: `python --version`, `robot --version`, `locust --version`
  and `pip show robotframework-locust`,
- your OS. Studio bugs can differ between Windows and Linux.

Never paste a token, a password or an internal host name. The library masks
secrets in the Robot log, but a console paste is not masked.

## Set up

You need Python 3.11 or newer and [uv](https://docs.astral.sh/uv/).

```
git clone https://github.com/ai94iq/robotframework-locust
cd robotframework-locust
uv sync --all-groups
```

For Studio work, also install the extra: `uv pip install -e ".[studio]"`.

## Checks

Run all of these from the repo root before you open a merge request. Every
one must pass:

```
uv run ruff check src tests evals
uv run mypy src evals/hooks/mr_guard.py
uv run pytest
uv run bandit -c pyproject.toml -r src
uv run pip-audit
uv run python evals/hooks/mr_guard.py
```

`pytest` fails under 80% coverage of `src/LocustLibrary`. Studio
(`src/LocustLibrary/studio/`) is outside that gate, and its Qt tests skip
when PySide6 is not installed. A change to Studio needs those tests run with
the `studio` extra installed.

`evals/hooks/mr_guard.py` is the gate for a merge request. It fails a change
that lowers the coverage gate, opens Locust beyond 127.0.0.1, removes the
gevent patch, accepts a blank keyword name, or starts Locust from a test.

CI runs the same checks when a release is published, not on each push. Run
them yourself before you push.

## Rules for a change

- Locust listens on every interface by default. Keep the master, the workers
  and the web UI on 127.0.0.1.
- Run Load Test patches gevent before it builds a Locust environment. Do not
  remove that call, and do not import Locust at module level in a new file
  that runs before it.
- Time values accept `ms`. Locust's own parser does not, so check `ms`
  before `s`.
- A new keyword gets a docstring, because libdoc builds the keyword reference
  from it. Add it to the keyword table in `docs/library.md`.
- A change a user can see gets a line in `CHANGELOG.md` and an update to the
  docs page it touches.

## Tests

Write the test first and see it fail for the reason you expect. A test calls
the keyword the way a suite does and checks what the suite would see.

Tests never start a listening Locust process or open a port. Mock
`subprocess.Popen` instead. The merge-request hook rejects a test that
starts Locust.

## Commits and merge requests

Commit titles start with a type: `feat:`, `fix:`, `docs:`, `test:`,
`refactor:` or `ci:`, then a short plain sentence, such as
`fix: let Studio start Robot on Linux`. The body says why.

Keep one change per merge request. Say in the description which checks you
ran and how you tested the change by hand, if you did.

## Security

Report a security problem privately through the repo's security advisories,
not in a public issue.

## k6 converter internals

1. The options reader first reads `export const options` straight from the
   script, when every value in it is a literal (`static_options` in
   `src/LocustLibrary/k6/scan.py`). This runs no k6 and needs no
   `--trust-script`. The report row is `options | read statically`.
   When an option is computed, the reader falls back to
   `k6 inspect --execution-requirements`, which gives the resolved options:
   scenarios, thresholds, the TLS flag and the total duration. The call has a
   60 s timeout (`run_inspect` in `src/LocustLibrary/k6/options.py`). k6 runs
   the script's init (top-level) code as you, so convert only scripts you trust
   (see [docs/safety.md](docs/safety.md)). The fallback runs only when you pass
   `--trust-script`. Without it, the command exits 1 with a one-line reason
   that names the option that is not a literal, and writes no files. The report
   row is then `options | from k6 inspect`. The converter never calls `k6 run`. k6 gets only these environment variables:
   `PATH`, `SYSTEMROOT`, `HOME`, `USERPROFILE`, `TEMP`, `TMP` and `TMPDIR`, when
   set. `__ENV` in init code sees those and the `-e` pairs, nothing else.
2. The scanner (`src/LocustLibrary/k6/scan.py`) parses the script with
   tree-sitter and reads each exported function. It marks each function plain
   (converted to Python calls) or hand port (you write it). See
   [Plain and hand port functions](#plain-and-hand-port-functions).
3. The emitter (`src/LocustLibrary/k6/emit.py`) maps what k6 and LocustLibrary
   share into Robot keywords. Every item it cannot map exactly gets a report row.
   `profile.py` maps scenarios and thresholds to keyword lines, and
   `robot_files.py` writes the suite, resources and Python tasks.

## Research sources

Sources read while the library was designed. They are not user docs.

### Taurus


### rfswarm

- rfswarm (RF-native load tool): https://github.com/damies13/rfswarm

### Robot Framework

- robotframework-oxygen (Locust handler pattern): https://github.com/eficode/robotframework-oxygen
- pabot: https://github.com/mkorpela/pabot
- robotframework-qtexpert (Qt RF library): https://pypi.org/project/robotframework-qtexpert/

### Python packaging and tooling

- Python Packaging User Guide: https://packaging.python.org
- Writing pyproject.toml: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Trusted publishing: https://docs.pypi.org/trusted-publishers/
- Ruff settings: https://docs.astral.sh/ruff/settings/

### Concurrency (gevent)

- gevent monkey patching: http://www.gevent.org/api/gevent.monkey.html
- Celery gevent docs: https://docs.celeryq.dev/en/stable/userguide/concurrency/gevent.html

### arXiv papers

- Vanguard (adaptive load testing): https://arxiv.org/html/2606.22013v1
- RELOAD (RL-driven load testing): https://arxiv.org/html/2506.04204v1
- LLMRunner: https://arxiv.org/html/2605.24217
- Mesh2 (Locust + K8s resilience): https://arxiv.org/html/2603.04782v1
- Change-point detection for performance: https://arxiv.org/pdf/2610.09023v1
- Greenlet/gevent concurrency: https://arxiv.org/html/2507.16109v1
- Distributed load testing: https://arxiv.org/html/2408.08148v1
- Performance regression: https://arxiv.org/html/2609.17179v1

### PySide / Qt

- PySide6 docs: https://doc.qt.io/qtforpython-6/
- PySide6 deployment: https://doc.qt.io/qtforpython-6/deployment/index.html
- pyqtgraph: https://www.pyqtgraph.org
- QDarkStyleSheet: https://github.com/ColinDuquesnoy/QDarkStyleSheet
- pyqtdarktheme: https://github.com/5yutan5/pyqtdarktheme

### Security and quality

- bandit: https://bandit.readthedocs.io
- pip-audit: https://pypi.org/project/pip-audit/
- detect-secrets: https://github.com/Yelp/detect-secrets
- ruff: https://docs.astral.sh/ruff/

### Other

- python-skills (wdm0006): https://github.com/wdm0006/python-skills
