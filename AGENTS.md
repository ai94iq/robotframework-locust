# Agent guide

This repo is a Robot Framework library that drives Locust. It is not the
Locust project. Change `src/LocustLibrary/` and `tests/`.

## Checks

From the repo root, these three must pass:

```
uv run ruff check src tests
uv run mypy src
uv run pytest
```

`pytest` fails under 80% coverage of `src/LocustLibrary`. `src/LocustLibrary/studio/`
is omitted. Do not lower `fail_under` to make a red run pass.

## Loopback

Locust listens on every interface when `--master-bind-host` is omitted.
`--master-bind-host` defaults to `*`. An empty `--web-host` also listens on
every interface. A worker does not start a web UI.

`run_distributed` must pass `--master-bind-host 127.0.0.1` and
`--web-host 127.0.0.1` on the master command. Workers dial
`--master-host 127.0.0.1` and must not get `--web-host`.

`start_web_ui` allows only `127.0.0.1`, `localhost`, and `::1`. Do not add
`--web-login`. Locust's login flag needs a custom auth page in the locustfile.

Tests must not start a listening Locust process. Mock `subprocess.Popen`.

## Gevent

`run_load_test` calls `_patch_gevent` before it builds a Locust environment.
That sets `LOCUST_SKIP_MONKEY_PATCH` and then patches gevent once. Do not
remove that call. Do not import Locust at module level in a new file that
runs before `_patch_gevent`.

## Library rules

`LocustLibrary` stays CamelCase. `N999` is ignored for that reason.

`_parse_time` and `_parse_seconds` accept `ms`. Locust's own `parse_timespan`
does not. Check `ms` before `s`.

`Add Task`, `Set On Start`, and `Set On Stop` call `BuiltIn.run_keyword` and
record an `RF` stat. A blank keyword name is rejected.
