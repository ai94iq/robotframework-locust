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
pip install ".[k6]"      # tree-sitter parsers, reserved for the k6 converter
```

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
| Create Load Test | host, verify_tls=True, proxy= | Starts a scenario. The host is an http or https URL with no user name or password. |
| Add User Class | name, weight=1, fixed_count=0 | Starts a user class. Later tasks and waits belong to it. |
| Set Wait Time | minimum, maximum | Think time between tasks. |
| Set Load Stages | *stages | Ramps users over `duration:users` stages, such as `2m:20`. With stages, Run Load Test ignores users, spawn rate and run time. |
| Add Get Request | name, path, weight=1, expected_status=200, headers= | Adds a GET task. Only the listed status codes pass. |
| Add Post Request | name, path, weight=1, expected_status=200, headers=, json=, data= | Adds a POST task with a JSON or form body. |
| Add Task | name, keyword, weight=1 | Adds a task that runs a Robot Framework keyword. |
| Add Python Task | name, function, weight=1 | Adds a task that calls `module.function` with the Locust user. |
| Set On Start | keyword_name | Sets the keyword each user runs when it starts. |
| Set On Stop | keyword_name | Sets the keyword each user runs when it stops. |
| Run Load Test | users=10, spawn_rate=1.0, run_time=30s, csv_prefix=locust, iterations=0, max_users=100 | Runs the scenario headless. Refuses the run before it starts if the peak user count is above max_users. iterations caps the task runs for all users together. |
| Get Locust Stats | none | Returns the stats rows, the aggregated row and the fail ratio as a dict. |
| Get Aggregated Stats | none | Returns the aggregated stats row as a dict. |
| Should Have No Failures | none | Fails if any request failed. |
| Should Meet Response Time | endpoint, percentile, maximum | Fails if the percentile is above the maximum. Use an endpoint name, or `aggregated` for all requests. |
| Should Meet Throughput | minimum | Fails if requests per second is below the minimum. |
| Should Meet Error Rate | maximum, endpoint= | Fails if the error rate is above the maximum, such as `1%`. Checks all requests, or one endpoint. |
| Export Report | base_path=locust | Writes the CSV stats files for the last run and returns the base path. |
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

In progress. The library does not convert k6 scripts yet. The converter will
read a k6 script through `k6 inspect` only. That command reads the script's
options and does not run the test. The converter will never call `k6 run`.

## Sources

See `docs/references.md` for the Locust and Robot Framework sources.
