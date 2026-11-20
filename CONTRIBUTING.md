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
