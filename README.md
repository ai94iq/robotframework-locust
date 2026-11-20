# robotframework-locust

Robot Framework library that builds and runs Locust load tests headless.
You write the load test as a Robot suite: the library creates the Locust
users, runs them, and checks the stats with keywords.

The library uses Locust (2.30 or newer, below 3) for the load itself.

## Contents

- Install
- Example suite
- Keywords
- Safety limits
- k6 converter
- Sources

## Install

Requires Python 3.11 or newer. Robot Framework 7.5 or newer and Locust are
installed with the library.

From a checkout of this repository:

```
uv sync                  # uv: creates .venv with the library installed
uv pip install .         # uv: into the current environment
pip install .            # pip
```

Optional extras:

```
pip install ".[studio]"  # adds the locust-studio command (PySide6, pyqtgraph)
pip install ".[k6]"      # tree-sitter parsers for the rflocust-k6 command
```

## Locust Studio

`locust-studio` opens a desktop window. **Open suite...** (Ctrl+O) reads a
`.robot` load suite with a Robot dry run, so nothing is sent, and lists its
user classes and their tasks. **Run** (Ctrl+R) runs the suite under Robot at
low priority into a temporary output folder. During the run, Studio shows the
Robot console and Locust's three report charts, updated every second:
requests and failures per second, the 50th and 95th percentile response
times, and users. When the run ends, the Report tab shows Locust's statistics
table. Its buttons open the Robot log and the Locust HTML report that
`Export Report` wrote. With no suite open, Run runs the HTTP tasks put
together on the Build tab.

Run Load Test writes the live feed only when the `LOCUSTLIBRARY_FEED`
environment variable names a file. Studio sets it for its own runs.

Studio has two themes, picked on the Settings tab: Graphite (dark, the
default) and Paper (light). DESIGN.md describes both. Studio ships the Inter
and JetBrains Mono fonts under the SIL Open Font License 1.1
(`studio/fonts/`); without them it falls back to Segoe UI and Consolas.

## Example suite

`home_load.robot` is a short suite. It has one scenario with two GET
requests, a ramp, and checks on the results:

```robotframework
*** Settings ***
Library    LocustLibrary

*** Test Cases ***
Home Page Under Load
    Create Load Test    https://example.com
    Set Wait Time    1s    3s
    Add Get Request    home    /    expected_status=200
    Add Get Request    health    /health    weight=2    expected_status=200, 204
    Set Load Stages    30s:10    1m:10    15s:0
    Run Load Test    max_users=50
    Should Have No Failures
    Should Meet Response Time    home    p95    800ms
    Export Report    home-run
```

Run it with Robot Framework:

```
robot home_load.robot
```

## Keywords

All keywords are in the `LocustLibrary` library. Arguments with no default
are required. Time values take `500ms`, `30s`, `2m`, `1h`, or plain seconds.

| Keyword | Arguments | What it does |
|---|---|---|
| Create Load Test | host, verify_tls=True, proxy=, allowed_hosts= | Starts a scenario. The host is an http or https URL with no user name or password. If an allowlist is set, the host name must be on it. |
| Add User Class | name, weight=1, fixed_count=0 | Starts a user class. Later tasks and waits belong to it. |
| Set Wait Time | minimum, maximum | Think time between tasks. |
| Set Pacing | interval | Starts a task run every interval per user, whatever the response time (Locust constant_pacing). A run that takes longer starts the next at once. Replaces Set Wait Time for the class. |
| Add Stop Rule | rule | Stops the run once the rule holds for its whole window, such as `p95 > 1s for 10s` or `rc5?? > 20% for 5s, stop as passed`. See Safety limits. |
| Set Load Stages | *stages | Ramps users over `duration:users` stages, such as `2m:20`. With stages, Run Load Test ignores users, spawn rate and run time. |
| Add Get Request | name, path, weight=1, expected_status=200, headers=, expected_text= | Adds a GET task. Only the listed status codes pass. With expected_text, the body must also contain that text. |
| Add Post Request | name, path, weight=1, expected_status=200, headers=, json=, data=, expected_text= | Adds a POST task with a JSON or form body. With expected_text, the body must also contain that text. |
| Add Task | name, keyword, weight=1 | Adds a task that runs a Robot Framework keyword. |
| Add Python Task | name, function, weight=1 | Adds a task that calls `module.function` with the Locust user. |
| Set On Start | keyword_name | Sets the keyword each user runs when it starts. |
| Set On Stop | keyword_name | Sets the keyword each user runs when it stops. |
| Run Load Test | users=10, spawn_rate=1.0, run_time=30s, iterations=0, max_users=100, stop_on_fail_ratio=0, fail_ratio_warmup=10s | Runs the scenario headless. Refuses the run before it starts if the peak user count is above max_users. iterations caps the task runs for all users together. The log gets a stats table per request name and the first 3 calls of each name plus up to 50 failed calls, in RequestsLibrary style. Passwords, client secrets, tokens, OTP fields and auth headers show as `***`. With verify_tls off, it logs one warning per host. With stop_on_fail_ratio set, the run stops early when failures pass it. |
| Get Locust Stats | none | Returns the stats rows, the aggregated row and the fail ratio as a dict. |
| Get Aggregated Stats | none | Returns the aggregated stats row as a dict. |
| Should Have No Failures | none | Fails if any request failed. |
| Should Meet Response Time | endpoint, percentile, maximum | Fails if the percentile is above the maximum. Use an endpoint name, or `aggregated` for all requests. |
| Should Meet Throughput | minimum | Fails if requests per second is below the minimum. |
| Should Meet Error Rate | maximum, endpoint= | Fails if the error rate is above the maximum, such as `1%`. Checks all requests, or one endpoint. |
| Export Report | base_path=locust | Writes `<base>_stats.csv` and the Locust HTML report `<base>.html` into the Robot output folder, links the HTML report in the log, and returns the base path. |
| Start Locust Web | locustfile, port=8089 | Starts the Locust web UI in a subprocess, on 127.0.0.1. |
| Stop Locust Web | none | Stops the web UI that Start Locust Web started. |
| Run Distributed | locustfile, processes=2 | Starts a master and worker processes on this machine. |
| Stop Distributed | none | Stops the master and the workers. |

Argument formats:

- `expected_status` takes one code (`200`), a comma list (`200, 204`),
  or a list.
- Stages take `duration:users`, such as `2m:20`.
- Percentiles take `50`, `90`, `95`, `99` or `999`, with or without the `p`.

## Safety limits

Read these before you run a test against a host you do not own.

- **Peak user ceiling.** Run Load Test refuses a run before Locust starts when
  its peak user count is above `max_users` (default 100). The peak is the
  highest stage user count, or `users` when there are no stages, or the sum
  of the `fixed_count` values of the user classes if that sum is higher. To
  run more users, pass a higher `max_users` on purpose.
- **Host allowlist.** Create Load Test checks the host name against
  `allowed_hosts` (a comma list), or against the
  `LOCUSTLIBRARY_ALLOWED_HOSTS` environment variable when the argument is
  empty. A host that is not on the list is refused before any request. With
  no list set, the host is accepted and the log shows one warning.
- **Failure breaker.** `stop_on_fail_ratio` on Run Load Test, such as `20%`,
  stops the run when the share of failed requests goes over it. The check
  starts after `fail_ratio_warmup` (default 10s) and runs every half second.
  The log shows the reason as a warning. The default 0 turns it off.
- **Stop rules.** `Add Stop Rule    p95 > 1s for 10s` stops the run once the
  value stays over the limit for the whole window, checked every half second.
  Metrics: `pN` (Locust's current response time percentile, `ms` or `s`),
  `fail` (share of failed requests), `rcNNN` (share of responses whose code
  matches; `?` and `*` match digits), and `cpu` and `mem` (the load
  machine, so an overloaded generator stops the run instead of skewing it).
  `fail` and `rc` count only the requests since the last check; a check with
  no responses leaves the window as it is. By default a rule fails Run Load
  Test; end it with `, stop as passed` to only stop. The syntax follows
  Taurus pass/fail criteria.
- **Body check.** A server can answer 200 with an error page. Pass
  `expected_text` to Add Get Request or Add Post Request, and a response
  without that text counts as a failure.
- **No requests, no pass.** The Should keywords fail when the run, or the
  endpoint they check, recorded no requests.
- **Busy load generator.** When Locust sees this machine's CPU above 90%,
  Run Load Test logs a warning. Response times from such a run can be too
  high, because the generator itself is slow.
- **Web UI on loopback.** Start Locust Web binds 127.0.0.1 only. The keyword
  has no host argument, so other machines cannot reach the web UI through it.
- **Distributed mode stays on this machine.** Run Distributed binds the master
  and connects the workers on 127.0.0.1. It does not spread load across
  machines.
- **TLS checks.** `verify_tls=False` on Create Load Test skips certificate
  checks, as k6 insecureSkipTLSVerify does. Use it only for test hosts with a
  self-signed certificate.
- **Proxy.** Locust ignores HTTPS_PROXY, because it turns off trust_env. Pass
  the proxy to Create Load Test as an `http://` URL. The library sends both
  http and https traffic through it.

## k6 converter

`rflocust-k6` turns a k6 script into a Robot project for this library. It
reads the script's options with `k6 inspect`, scans the exported functions
for plain HTTP calls, and writes a project folder. A function it cannot convert
becomes a stub that raises `NotImplementedError` until you port it by hand.

Install the extra. The k6 binary must also be on PATH, because `k6 inspect`
reads the options:

```
pip install ".[k6]"
rflocust-k6 script.js --out robot --env-name dev -e KEY=VALUE --max-users 100
```

The project folder has this layout:

```
robot/
  tests/<name>.robot                          thin suite, one test case
  collections/<name>_test_keywords.resource   Build, Run and Check keywords
  resources/resources.resource                entry file every suite imports
  resources/variables.resource                ENV switch, default dev
  resources/<env>_variables.resource          HOST and PROXY for one env
  resources/python/<name>_tasks.py            k6 functions as Python tasks
  reports/<name>.k6-report.md                 one row per item: status, note
```

Run the project from its folder, with the default `--out robot`:

```
robot -v ENV:dev robot/tests
```

No `--pythonpath` is needed. The entry resource imports LocustLibrary with
`python_path=${CURDIR}/python`, so Add Python Task finds the tasks modules. `resources/resources.resource` is rebuilt on each
run. `variables.resource` and the environment file are written only when
missing, so your edits to them survive a rerun.

Scripts with no thresholds get a `Should Have No Failures` check and an
approximate row in the report. The report marks each item as mapped,
approximate, hand port, clamped, set by hand or unsupported.

The converter never runs `k6 run`, but `k6 inspect` runs the script's init
code as you, so convert only scripts you trust. See
`docs/k6-converter.md` for the mapping table, the limits and how to port a
function by hand.

## Sources

See `docs/references.md` for the Locust and Robot Framework sources.
