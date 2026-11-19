---
name: checking-locust-library
description: Runs ruff, mypy, and pytest for robotframework-locust and holds the coverage gate. Use for "check the library", "run the tests", "is coverage green".
---

# Checking the Locust library

From the repo root, run exactly:

```
uv run ruff check src tests
uv run mypy src
uv run pytest
```

`pytest` fails under 80% coverage of `src/LocustLibrary`.
`src/LocustLibrary/studio/` is omitted from that gate. Do not lower
`fail_under` to make a red run pass.

A red check stays red until the cause is fixed. Do not skip a command.
Do not start a listening Locust process to get a green run. Mock
`subprocess.Popen`.
