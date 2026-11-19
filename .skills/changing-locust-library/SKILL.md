---
name: changing-locust-library
description: Keeps Locust spawn on loopback, leaves the gevent patch in place, and parses ms before s. Use for "change run_distributed", "web host", "Add Task", "gevent".
---

# Changing the Locust library

Edit `src/LocustLibrary/` and `tests/`. This repo is not the Locust project.

## Loopback

Locust listens on every interface when `--master-bind-host` is omitted.
That flag defaults to `*`. An empty `--web-host` also listens on every
interface. A worker does not start a web UI.

`run_distributed` passes `--master-bind-host 127.0.0.1` and
`--web-host 127.0.0.1` on the master command. Workers dial
`--master-host 127.0.0.1` and do not get `--web-host`.

`start_web_ui` allows only `127.0.0.1`, `localhost`, and `::1`. Do not add
`--web-login`. That flag needs a custom auth page in the locustfile.

Tests mock `subprocess.Popen`. They do not open a listen socket.

## Gevent

`run_load_test` calls `_patch_gevent` before it builds a Locust environment.
That sets `LOCUST_SKIP_MONKEY_PATCH` and then patches gevent once. Do not
remove that call. Do not import Locust at module level in a new file that
runs before `_patch_gevent`.

## Keywords and time

`LocustLibrary` stays CamelCase. `N999` is ignored for that reason.

`_parse_time` and `_parse_seconds` accept `ms`. Locust's `parse_timespan`
does not. Check `ms` before `s`.

`Add Task`, `Set On Start`, and `Set On Stop` call `BuiltIn.run_keyword`
and record an `RF` stat. A blank keyword name is rejected.

After a change, follow `.skills/checking-locust-library/SKILL.md`.
