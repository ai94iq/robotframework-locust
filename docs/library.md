# Library guide

How to write a load suite with LocustLibrary. Every keyword, with its
arguments and examples, is also in the keyword reference that libdoc builds:
`docs/keywords.html`, or the GitHub page.

## Contents

- [A first suite](#a-first-suite)
- [How a run works](#how-a-run-works)
- [Keyword table](#keyword-table)
- [Several user classes](#several-user-classes)
- [Python tasks](#python-tasks)
- [Data per user and shared data](#data-per-user-and-shared-data)
- [Reports](#reports)
- [Environment variables](#environment-variables)

## A first suite

```robotframework
*** Settings ***
Library    LocustLibrary

*** Test Cases ***
Home Page Under Load
    Create Load Test    https://test.example.com    allowed_hosts=test.example.com
    Set Wait Time    1s    3s
    Add Get Request    home    /    expected_status=200
    Add Get Request    health    /health    weight=2    expected_status=200, 204
    Add Stop Rule    p95 > 2s for 10s
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

## How a run works

A suite has three parts.

A scenario is the load test that one Create Load Test call builds: one target
host, its user classes and tasks, and the stages and stop rules for the run.

1. Build: Create Load Test starts a scenario for one host. The Add and Set
   keywords add users, tasks, waits, stages and stop rules to it.
2. Run: Run Load Test runs that scenario. It starts Locust headless in the
   Robot process and waits until the run ends. A stop rule or the failure
   breaker (`stop_on_fail_ratio`, see the keyword table) can end it early;
   by default that also fails the run. The first Run Load Test calls
   `gevent.monkey.patch_all()`, which changes the standard sockets, threads
   and sleeps for the whole Robot process until it ends.
3. Check: the Should keywords read the stats of that run and fail the test
   when a number is out of bounds. They fail when the run recorded no
   requests.

## Keyword table

All keywords are in the `LocustLibrary` library. Arguments with no default
are required. Time values take `500ms`, `30s`, `2m`, `1h`, or plain seconds.
One exception: a stop rule window takes seconds with an `s` only (`for 60s`),
and a stop rule limit takes `ms`, `s` or `%`.

| Keyword | Arguments | What it does |
|---|---|---|
| Create Load Test | host, verify_tls=True, proxy=, allowed_hosts= | Starts a new scenario and drops the one before it. See [Create Load Test details](#create-load-test-details). |
| Add User Class | name, weight=1, fixed_count=0 | Starts a user class. Later tasks and waits belong to it. |
| Set Wait Time | minimum, maximum | Think time between tasks of the current user class, a random time from minimum to maximum. Optional: with no call, a class waits 1 to 3 seconds. A later call replaces the earlier one. |
| Set Pacing | interval | Starts a task run every interval per user, whatever the response time (Locust constant_pacing). A run that takes longer starts the next at once. For the class, pacing wins over Set Wait Time, whichever is called first. A later call replaces the interval. |
| Add Stop Rule | rule | Adds a rule; each call adds one more. The form is `<metric> > <limit> for <window>`. Metrics are `pN` (a percentile, such as `p95`), `fail`, `rcNNN` (a status code share; `?` and `*` match a digit), `cpu`, `mem` and `idle`. See the [metric list](safety.md#limits-during-the-run). Stops the run once the rule holds for its whole window, such as `p95 > 1s for 10s`, `idle > 30s` or `rc5?? > 20% for 5s, stop as passed`. `idle` is the time with no completed response. By default a rule that stops the run also fails Run Load Test; `, stop as passed` only stops it. See [Safety limits](safety.md). |
| Set Load Stages | *stages | Ramps users over `duration:users` stages, such as `2m:20`. With stages, Run Load Test ignores users, spawn rate and run time. A later call replaces all stages. |
| Add Get Request | name, path, weight=1, expected_status=200, headers=, expected_text= | Adds a GET task. Only the listed status codes pass. With expected_text, the body must also contain that text. |
| Add Post Request | name, path, weight=1, expected_status=200, headers=, json=, data=, expected_text= | Adds a POST task with a JSON or form body. With expected_text, the body must also contain that text. |
| Add Task | name, keyword, weight=1 | Adds a task that runs a Robot Framework keyword. keyword is required; an empty value is refused. Each run shows in the stats as an `RF` request named after the keyword. A keyword that fails counts as a failed `RF` request. |
| Add Python Task | name, function, weight=1 | Adds a task that calls `module.function` with the Locust user. |
| Get User Index | | Inside a task keyword: the number of the virtual user running it, unique within the run. Use it for a unique value or data row per user. Python tasks read `user.index`. |
| Get User Iteration | | Inside a task keyword: how many task runs this user has started, counting this one. Python tasks read `user.iteration`. |
| Put Shared Value | name, value | Adds a value under a name for another user's step to take, such as an id one step created. A name holds at most `shared_limit` values (a library import argument, default 10000, 0 for no limit). One more fails the keyword. The limit is per name; nothing caps the total over all names. |
| Take Shared Value | name, timeout=10s | Takes the oldest value under the name, waiting up to timeout for one. The wait yields, so other users keep running while one user waits. Each value goes to one taker. With none in time the keyword fails and records a failed `SHARED` request named `Take Shared Value <name>`, so the task counts as a failure. Run Load Test starts with no values. |
| Set On Start | keyword_name | Sets the keyword each user of the current user class runs when it starts. Call it after Add User Class; with no Add User Class, it applies to the default class: the class that Create Load Test makes. The first Add User Class call drops the default class if it has no tasks yet. A later call replaces the keyword. |
| Set On Stop | keyword_name | Sets the keyword each user of the current user class runs when it stops. Scope and order are the same as for Set On Start. |
| Run Load Test | users=10, spawn_rate=1.0, run_time=30s, iterations=0, max_users=100, stop_on_fail_ratio=0, fail_ratio_warmup=10s, breaker_fails=True, fail_on_busy_cpu=False | Runs the scenario headless and waits until it ends. See [Run Load Test details](#run-load-test-details). |
| Get Locust Stats | none | Returns a dict with `rows` (a list of row dicts, one per request name), `aggregated` (one row dict, or None) and `fail_ratio` (a fraction from 0 to 1). Returns an empty dict before Run Load Test. |
| Get Aggregated Stats | none | A shorthand for the `aggregated` value of Get Locust Stats. Returns an empty dict before Run Load Test. |
| Should Have No Failures | none | Fails if any request failed. |
| Should Meet Response Time | endpoint, percentile, maximum | Fails if the percentile is above the maximum. Use an endpoint name, or `aggregated`, `total` or an empty name for all requests. |
| Should Meet Throughput | minimum | Fails if requests per second over the whole run is below the minimum. The minimum is a plain number in requests per second, such as `5`. |
| Should Meet Error Rate | maximum, endpoint= | Fails if the error rate is above the maximum, such as `1%`. Checks all requests, or one endpoint. |
| Export Report | base_path=locust | Writes `<base>_stats.csv` and the Locust HTML report `<base>.html` into the Robot output folder, links the HTML report in the log, and returns the base path. Files with the same base are overwritten. Before Run Load Test it fails. The HTML file is written only when Locust made a report. |
| Start Locust Web | locustfile, port=8089, host=, allowed_hosts= | Starts the Locust web UI for a locustfile (a path to an existing file) in a subprocess and returns at once. The UI is at `http://127.0.0.1:<port>`. The UI has no login and no user ceiling: any account or process on this machine can open it and start a run of any size. A second call stops the first UI. A relative path is read from the current working directory. The library does not check the port; a busy port makes the Locust process fail. host is the target URL, checked against allowed_hosts like Create Load Test. |
| Stop Locust Web | none | Stops the web UI that Start Locust Web started. |
| Run Distributed | locustfile, processes=2, host=, allowed_hosts=, users=0, max_users=100 | Starts a master and `processes` workers for a locustfile on this machine and returns at once. The master binds to 127.0.0.1 only. A second call stops the first set. A relative path is read from the current working directory. The master uses port 5557; the library does not check that it is free. host is checked like Create Load Test. users=0 starts no users; the run waits for a start from the master's web UI. users above 0 makes the master start that many users at once (`--autostart`). users above max_users is refused before the start. |
| Stop Distributed | none | Stops the master and the workers. |

Argument formats:

- `expected_status` takes one code (`200`), a comma list (`200, 204`),
  or a list.
- `headers` takes a dictionary of header names and values, such as one made with
  `Create Dictionary    Accept=application/json`.
- `json` takes a dictionary or list; it is sent as a JSON body with
  `Content-Type: application/json`.
- `data` takes a dictionary, sent form-encoded, or a string, sent as is.
- Example: `Add Post Request    login    /login    json=${body}    headers=${headers}`,
  where `${body}` is `Create Dictionary    user=a    pass=b`.
- Stages take `duration:users`, such as `2m:20`.
- Percentiles take `50`, `90`, `95`, `99` or `999`, with or without the `p`.
  `999` is the 99.9th percentile; `p99.9` also works.

A stats row dict has the keys `name`, `request_count`, `failure_count`,
`median`, `average`, `min`, `max`, `p50`, `p90`, `p95`, `p99` and `p999`
(response times in milliseconds), and `rps` and `failures_s` (per second).

Start Locust Web and Run Distributed run your own locustfile in separate
Locust processes. The scenario built by the Add and Set keywords does not
apply to them. Neither do stop rules, shared values or user indexes. The
Should keywords do not read their stats. Stop them with Stop Locust Web and Stop Distributed, which wait up to
10 seconds per process and then kill it.

### Create Load Test details

- The host is an http or https URL with no user name or password.
- `allowed_hosts` is a comma list of host names. Spaces around each name
  are dropped; the match ignores case and the port, and subdomains do not
  match. With an empty value, the `LOCUSTLIBRARY_ALLOWED_HOSTS` variable
  is used. See [Limits before the run](safety.md#limits-before-the-run).
- `verify_tls=False` skips the TLS certificate check.
- `proxy` is an `http://` proxy URL. Every http and https request of the
  run goes through it; there is no bypass list. Locust ignores the
  `HTTPS_PROXY` environment variable, so set the proxy here. With an empty
  value, no proxy is used.
- A second Create Load Test starts again from nothing: user classes, tasks,
  stages, stop rules and the stats of the last run are dropped.

### Run Load Test details

- `spawn_rate` is users started per second. `iterations` caps the task
  runs for all users together; `0` means no cap.
- The run is refused before it starts if the peak user count is above
  `max_users`. See [Several user classes](#several-user-classes) and
  [Limits before the run](safety.md#limits-before-the-run).
- `stop_on_fail_ratio` sets the failure breaker: when the failure ratio goes
  over it, after `fail_ratio_warmup`, the run stops early. A breaker stop
  fails the keyword; `breaker_fails=False` lets it pass.
- A load generator CPU over 90% logs a warning; `fail_on_busy_cpu=True`
  fails the keyword instead.
- With `verify_tls` off, it logs one warning per host.
- The log gets a stats table and sample calls; see [Reports](#reports).
- Run Load Test can be called again. It runs the current scenario once more,
  with no shared values, and its stats replace those of the last run.

### One load run per process

In one Robot process, the library runs one load at a time. A second Start
Locust Web call stops the first UI, and a second Run Distributed call stops
the first set. The master port is always 5557, and Start Locust Web uses
8089 unless you pass `port`. Parallel Robot processes, such as pabot
runs, do not share this state. They do share ports and the
`LOCUSTLIBRARY_FEED` file, so give each its own web `port`, run one Run
Distributed at a time, and give each its own feed file.

## Several user classes

Add User Class starts a class. The tasks, waits and pacing that follow belong
to it, until the next Add User Class:

```robotframework
Create Load Test    https://test.example.com
Add User Class    Browser    weight=3
Set Wait Time    0.5s    2s
Add Get Request    items    /items
Add User Class    Checker    fixed_count=2
Set Pacing    5s
Add Get Request    health    /health
Run Load Test    users=20    run_time=2m
```

`fixed_count` gives a class an exact number of users, taken out of
`users`, not added on top. Locust starts the fixed users first and shares
the rest out by `weight` among the classes with no `fixed_count`. In the
example, Checker gets 2 users and Browser gets the other 18.

With Set Load Stages, the same split applies to the user count of each
stage: with a `1m:10` stage, Checker gets 2 and Browser gets 8.

The sum of the `fixed_count` values counts toward the peak that `max_users`
checks; see [Limits before the run](safety.md#limits-before-the-run) for the
full rule. Run Load Test does not refuse or clamp a `fixed_count` sum above `users`.
For example, with `users=2` and a class with `fixed_count=5`, the peak is 5:
`max_users=4` refuses the run, and `max_users=100` lets it start. Only 2
users run, fixed users first, but the `max_users` check uses the peak of 5.
So the check can refuse a load that would never run.

With stages, each stage caps the users. With a `1m:3` stage and a class
with `fixed_count=5`, at most 3 users run in that stage. The peak for
`max_users` is still 5, the higher of the top stage count and the
`fixed_count` sum.

## Python tasks

Import arguments:

| Argument | Default | What it does |
|---|---|---|
| python_path | empty | A folder put first on the Python module search path, for the modules Add Python Task names. Empty adds nothing. A relative path is read from the current working directory, so use `${CURDIR}`. |

Add Python Task calls `module.function` with the Locust user, so a task can
use `user.client` like a locustfile does. Pass the folder of the module when
you import the library:

```robotframework
*** Settings ***
Library    LocustLibrary    python_path=${CURDIR}/python

*** Test Cases ***
Checkout Under Load
    Create Load Test    https://test.example.com
    Add Python Task    checkout    checkout_tasks.checkout
    Run Load Test    users=5    run_time=1m
```

```python
def checkout(user):
    user.client.post("/cart", json={"sku": "A-100"}, name="add to cart")
    user.client.post("/checkout", name="checkout")
```

Add Task runs a Robot keyword as the task instead.

## Data per user and shared data

All users share one Robot process, so Robot variables are shared between
them. Read per-user values with these keywords:

- Get User Index returns the number of the user that runs the task. Use it to
  pick a unique data row or build a unique name.
- Get User Iteration returns how many task runs this user has started.

Python tasks read the same values as `user.index` and `user.iteration`.

One step can hand data to another step during a run. Put Shared Value adds a
value under a name. Take Shared Value takes the oldest value under that name,
and waits up to its timeout for one. Each value goes to one taker.
In this example, add Create Order and Pay Order as tasks with Add Task in the
same scenario. A Pay Order run takes a value that a Create Order run put:

```robotframework
Create Order
    ${id}=    Create Order Through The Api
    Put Shared Value    order    ${id}

Pay Order
    ${id}=    Take Shared Value    order    timeout=10s
    Pay Order Through The Api    ${id}
```

Run Load Test starts with no shared values. A name holds at most
`shared_limit` values (default 10000); one more fails Put Shared Value.
Set it at import, such as `Library    LocustLibrary    shared_limit=500`.
A Take Shared Value timeout shows as a failed `SHARED` request.

## Reports

Run Load Test writes to the Robot log:

- a stats table per request name,
- the first 3 calls of each name and up to 50 failed calls, in RequestsLibrary
  style. The values of the `Authorization`, `Proxy-Authorization`,
  `Cookie` and `Set-Cookie` headers show as `***`. The `password`,
  `client_secret`, `access_token`, `refresh_token`, `id_token` and
  `otp` fields of JSON or form bodies also show as `***`. URLs, query
  strings and other headers, such as `X-Api-Key`, are logged as sent.
  JSON bodies are written out again as JSON, so spacing and key layout can
  differ from what was sent. A body over 10000 characters is cut and marked. The log and the HTML report are often shared, so
  do not put secrets in URLs.

Export Report writes `<base>_stats.csv` and the Locust HTML report
`<base>.html` beside `log.html`, and links the HTML report in the log.

## Environment variables

| Variable | What it does |
|---|---|
| `LOCUSTLIBRARY_ALLOWED_HOSTS` | Host allowlist, a comma list, when Create Load Test gets no `allowed_hosts`. |
| `LOCUSTLIBRARY_FEED` | A file that Run Load Test writes the live feed to, one JSON line per second. The file has no size cap and no rotation, so it grows for as long as the run lasts. The format is internal to Locust Studio and may change. Locust Studio sets it for its own runs. |
