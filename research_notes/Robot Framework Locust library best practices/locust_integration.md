# Locust (locustio) Integration and Programmatic Usage

## Programmatic Running (Environment, Runner, Events)

### Takeaway
Locust can be fully driven from Python via `Environment` + a `Runner` (local/master/worker) plus optional `WebUI`; lifecycle is controlled by `runner.start`, `runner.greenlet.join`, and `runner.quit`/`runner.stop`, with events for hooks.

### Cited Findings
- Create `Environment(user_classes=[...])`, then `env.create_local_runner()`; call `env.runner.start(user_count, spawn_rate=...)` and `env.runner.greenlet.join()` to block - [Locust docs use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html).
- `create_local_runner`, `create_master_runner`, `create_worker_runner` (last rarely makes sense; workers should be launched via CLI) - [Locust docs use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html).
- Full example spawns `stats_printer` and `stats_history` greenlets, fires `env.events.init`, starts web UI via `env.create_web_ui("127.0.0.1", 8089)`, stops with `gevent.spawn_later(30, runner.quit)` - [Locust docs use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html).
- `runner.spawn_users({UserClass.__name__: n})` manually spawns users (local runner only, experimental) - [Locust docs use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html).
- `Environment` accepts `events=events`; use event hooks (`events.init`, `events.test_start`, `events.test_stop`, `events.quitting`) - [Locust docs use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html) and [extending-locust](https://docs.locust.io/en/stable/extending-locust.html).
- `environment.process_exit_code` controls exit code; set in `@events.quitting` listener based on `environment.stats.total.fail_ratio`, `avg_response_time`, percentiles - [running-without-web-ui](https://docs.locust.io/en/2.30.0/running-without-web-ui.html).
- `runner.state` constants (`STATE_RUNNING`, `STATE_STOPPING`, etc.) used in background checkers - [extending-locust](https://docs.locust.io/en/stable/extending-locust.html).

### Inferences
- For Robot Framework, wrap the whole Locust run in a single keyword that builds Environment, runs, collects stats, and returns a pass/fail verdict; never call Locust from multiple RF threads.
- Use `LOCUST_SKIP_MONKEY_PATCH=1` when embedding Locust in a host that already patched or is incompatible (e.g. boto3) - [use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html).

### Gaps
- No official async/await API; everything is gevent-greenlet based.

## Creating Dynamic User Subclasses at Runtime

### Takeaway
User classes are created with `type(name, (HttpUser,), {...})` or a class body; tasks can be set via the `tasks` attribute as list/callables or `{callable: weight}` dict, and `abstract=True` base classes are not spawned. The `UserMeta` metaclass collects tasks at class creation.

### Cited Findings
- Tasks defined via `@task` decorator or `tasks` attribute (list of callables/TaskSets, or `{task: int}` dict, or `[(task, int), ...]` list) - [writing-a-locustfile](https://docs.locust.io/en/stable/writing-a-locustfile.html), [User source](https://docs.locust.io/en/latest/_modules/locust/user/users.html).
- `UserMeta.__new__` gathers tasks from base classes into `class_dict["tasks"]` - [User source](https://docs.locust.io/en/latest/_modules/locust/user/users.html).
- `abstract=True` means not spawned; `weight`, `fixed_count` control selection - [API User](https://docs.locust.io/en/stable/api.html).
- Tasks as normal functions receive the User instance as first arg: `def my_task(user): ...` - [writing-a-locustfile](https://docs.locust.io/en/stable/writing-a-locustfile.html).
- `execute_task` handles bound methods, TaskSet subclasses, and plain functions - [task source](https://docs.locust.io/en/latest/_modules/locust/user/task.html).

### Inferences
- A Robot Framework keyword can build a User subclass dynamically with `type("RFUser", (HttpUser,), {"host": host, "tasks": [task_fn]})` and pass it to `Environment(user_classes=[...])`.
- Keep task functions module-level (not closures capturing RF state) to avoid pickling/greenlet issues; inject config via `environment` or class attributes.

### Gaps
- No documented factory helper; dynamic creation relies on standard Python metaclass behavior.

## Greenlet Safety and gevent Monkey-Patching (RF Implications)

### Takeaway
Locust patches the stdlib with gevent at import time (`locust/__init__.py` calls `monkey.patch_all()` unless `LOCUST_SKIP_MONKEY_PATCH=1`); every virtual user is a greenlet on one OS thread, so blocking/CPU work stalls all users, and patching must happen before other modules capture original functions.

### Cited Findings
- `gevent.monkey.patch_all()` replaces socket/ssl/time/select/thread/os/subprocess etc.; must run early on main thread while single-threaded - [gevent monkey docs](http://www.gevent.org/api/gevent.monkey.html).
- Locust calls `monkey.patch_all()` on import; set `LOCUST_SKIP_MONKEY_PATCH=1` to skip - [use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html).
- Greenlet switching is cooperative: a greenlet that never yields (CPU-bound or C-extension I/O) blocks all others - [Tarragon knowledge card](https://tarrragon.github.io/blog/backend/knowledge-cards/gevent-monkey-patching).
- C-extension I/O (psycopg2/libpq, grpc without `grpc_gevent.init_gevent()`) bypasses patching - [Tarragon](https://tarrragon.github.io/blog/backend/knowledge-cards/gevent-monkey-patching), [locust issue 2339](https://github.com/locustio/locust/issues/2339).
- Python 3.11 + gevent known issue; upgrade greenlet to 3.0+ - [Celery gevent docs](https://docs.celeryq.dev/en/stable/userguide/concurrency/gevent.html).
- One Python process uses one CPU core; use multiple worker processes / `--processes` for more cores - [Tarragon](https://tarrragon.github.io/blog/backend/knowledge-cards/gevent-monkey-patching).

### Inferences
- In RF, import locust as early as possible (before RF's own imports of blocking libs) or set skip env var and patch manually at the very top of the RF suite entry.
- Avoid heavy CPU in task functions; offload to threadpool/process if needed.
- Use `--processes` (4.x) for multi-core load generation rather than threads.

### Gaps
- No RF-specific guidance from Locust; integration is ad-hoc.

## Stats API (RequestStats, Median, Percentiles, RPS, Failures, Error Rate)

### Takeaway
`environment.stats` is a `RequestStats`; `.total` is an aggregated `StatsEntry` with `num_requests`, `num_failures`, `avg_response_time`, `min/max_response_time`, `median_response_time`, `total_rps`, `current_rps`, `fail_ratio`, `get_response_time_percentile(p)`, and `.errors` for failure details.

### Cited Findings
- `RequestStats` holds `num_requests`, `num_none_requests`, `num_failures`, `total_response_time`, `min/max_response_time`, `num_reqs_per_sec`, `num_fail_per_sec` - [stats source](https://docs.locust.io/en/latest/_modules/locust/stats.html).
- `StatsEntry.get_response_time_percentile(percent)` (0-1) and `get_current_response_time_percentile` (last ~10s window) - [DeepWiki stats](https://deepwiki.com/locustio/locust/2.3-statistics-and-reporting).
- `stats.total.fail_ratio`, `avg_response_time`, `get_response_time_percentile(0.95)` used in quitting hook - [running-without-web-ui](https://docs.locust.io/en/2.30.0/running-without-web-ui.html).
- `PERCENTILES_TO_REPORT` default `[0.50, 0.66, 0.75, 0.80, 0.90, 0.95, 0.98, 0.99, 0.999, 0.9999, 1.0]` - [stats source](https://docs.locust.io/en/2.31.3/_modules/locust/stats.html).
- `stats.errors` dict of `StatsError` with `.occurrences`, `.to_name()` - [stats source](https://docs.locust.io/en/latest/_modules/locust/stats.html).
- Web UI `/stats/requests` returns JSON; `/stats/report` generates HTML - [DeepWiki](https://deepwiki.com/locustio/locust/2.3-statistics-and-reporting).

### Inferences
- For RF assertions, read `environment.stats.total` after run; compute thresholds (fail_ratio < 0.01, p95 < 800ms, etc.) and raise on violation.

### Gaps
- `median_response_time` property naming may differ by version; verify against installed version.

## Exporting CSV/HTML Reports Programmatically

### Takeaway
CSV export via `--csv=prefix` (stats, failures, exceptions, stats_history) at interval `CSV_STATS_INTERVAL_SEC` (default 1s); HTML via `--html=report.html`. Programmatically, use `StatsCSVFileWriter` or fetch `/stats/report`; on-demand generation via `get_html_report()`.

### Cited Findings
- `--csv example --headless -t10m` creates `example_stats.csv`, `example_failures.csv`, `example_exceptions.csv`, `example_stats_history.csv` - [retrieving-stats](https://docs.locust.io/en/stable/retrieving-stats.html).
- `locust.stats.CSV_STATS_INTERVAL_SEC = 5` to customize frequency - [retrieving-stats](https://docs.locust.io/en/stable/retrieving-stats.html).
- `--csv-full-history` appends all entries each write - [retrieving-stats](https://docs.locust.io/en/stable/retrieving-stats.html).
- `--html=report.html` auto-generates HTML report; `/stats/report` endpoint on-demand; `get_html_report()` - [DeepWiki](https://deepwiki.com/locustio/locust/2.3-statistics-and-reporting).
- `StatsCSVFileWriter(environment, percentiles, base_filepath, full_history=...)` opens files - [stats source](https://docs.locust.io/en/2.31.3/_modules/locust/stats.html).

### Inferences
- In programmatic mode, instantiate `StatsCSVFileWriter` and spawn a greenlet to write periodically, or call `env.runner.quit` after setting stats; simpler: pass `--csv`-equivalent by configuring `parsed_options` or invoke main flow. Most robust: generate CSV/HTML after run by reading `environment.stats` and using `StatsCSV`.
- For HTML, call web UI `/stats/report` endpoint or `get_html_report()` from `locust.html`.

### Gaps
- Exact programmatic CSV writer API signatures vary by version; confirm against installed 2.30+.

## Web UI vs Headless; --autostart; --processes (Distributed)

### Takeaway
Web UI is optional (`--headless` disables it and starts immediately); `--autostart` starts immediately while keeping UI; distributed uses `--master`/`--worker` (or `--processes N` to auto-spawn N local worker processes); master needs `--expect-workers` in headless mode.

### Cited Findings
- `--headless` disables web UI and starts immediately; use `-u` and `-t` - [running-without-web-ui](https://docs.locust.io/en/2.30.0/running-without-web-ui.html).
- `--autostart` starts immediately but keeps web UI; `--autoquit` quits X seconds after run finishes (with autostart) - [configuration](https://docs.locust.io/en/2.30.0/configuration.html).
- Distributed: one `--master`, N `--worker`; headless master uses `--expect-workers` - [running-without-web-ui](https://docs.locust.io/en/2.30.0/running-without-web-ui.html), [quickstart](https://docs.locust.io/en/stable/quickstart.html).
- `--processes 4` runs master + 3 workers in one command (4.x) - [configuration](https://docs.locust.io/en/2.30.0/configuration.html).
- Web UI programmatic: `env.create_web_ui(host, port)` + `web_ui.greenlet.join()` - [use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html).
- Web UI protects with `--web-login` - [configuration](https://docs.locust.io/en/2.30.0/configuration.html).

### Inferences
- For CI/RF automation, prefer headless programmatic mode; expose optional web UI on a configured port for debugging.

### Gaps
- `--processes` availability/version specifics not confirmed for all 2.30+; verify.

## Version Compatibility (Locust 2.30+, Python 3.11+)

### Takeaway
Target Locust 2.30+ (docs/examples reference 2.30.0/2.31.x/2.47); Python 3.11+ supported; gevent/greenlet must be compatible (greenlet 3.0+ for Python 3.11). Use `locust --version` and pin in requirements.

### Cited Findings
- Docs versions 2.30.0, 2.31.x, 2.47.0, 2.44.x, 2.45.x, 2.43.x - [docs.locust.io](https://docs.locust.io).
- Python 3.11 setup in CI example (`python-version: '3.11'`) - [running-without-web-ui stable](https://docs.locust.io/en/stable/running-without-web-ui.html).
- Python 3.11 + gevent known issue; upgrade greenlet to 3.0 - [Celery gevent](https://docs.celeryq.dev/en/stable/userguide/concurrency/gevent.html).
- Locust 2.x API: `Environment`, `create_local_runner`, `events`, `stats` stable since 2.x - [use-as-lib](https://docs.locust.io/en/stable/use-as-lib.html).

### Inferences
- Pin `locust>=2.30,<3` and `greenlet>=3.0` in the RF library's dependencies; test against latest 2.x.

### Gaps
- No explicit minimum Python version statement found; rely on gevent/locust wheel support.