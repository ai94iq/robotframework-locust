---
name: checking-locust-library
description: Runs ruff, mypy, pytest, and bandit for robotframework-locust and holds the coverage gate. Use for "check the library", "run the tests", "is coverage green".
---

# Checking the Locust library

From the repo root, run exactly:

```
uv run ruff check src tests evals
uv run mypy src evals/hooks/mr_guard.py
uv run pytest
uv run bandit -c pyproject.toml -r src
uv run python evals/hooks/mr_guard.py
```

`evals/hooks/mr_guard.py` fails the change when it drops the coverage gate,
the loopback flags, the worker dial address, the gevent patch, the blank
keyword check, or `BuiltIn.run_keyword`. A broad `except` that only passes
or returns fails too, as does a test that starts Locust, including through
`os.system`. A comment that names a public host does not. CI runs the hook
on every pull request.

`pytest` fails under 80% coverage of `src/LocustLibrary`.
`src/LocustLibrary/studio/` is omitted from that gate. Do not lower
`fail_under` to make a red run pass.

A red check stays red until the cause is fixed. Do not skip a command.
Do not start a listening Locust process to get a green run. Mock
`subprocess.Popen`.
