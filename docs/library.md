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

**Build a scenario**

- **Create Load Test**: starts a new scenario for one host and drops the one before it. See [Create Load Test details](#create-load-test-details).
- **Add User Class**: starts a user class. Later tasks and waits belong to it.
- **Set Wait Time**: sets the think time between tasks of the current class, a random time in a range. Without it, a class waits 1 to 3 seconds.
- **Set Pacing**: starts a task run every interval per user, whatever the response time. Pacing wins over Set Wait Time for the class.
- **Add Stop Rule**: adds a rule that stops the run when a metric holds for its whole window, such as `p95 > 1s for 10s`. See the [metric list](safety.md#limits-during-the-run).
- **Set Load Stages**: ramps users over stages, such as `2m:20`. A later call replaces all stages.
- **Add Get Request**: adds a GET task and the status codes that pass.
- **Add Post Request**: adds a POST task with a JSON or form body.
- **Add Task**: adds a task that runs a Robot Framework keyword.
- **Add Python Task**: adds a task that calls a function in a Python module with the Locust user.
- **Set On Start**: sets the keyword each user of the current class runs when it starts.
- **Set On Stop**: sets the keyword each user of the current class runs when it stops.

**Per-user data and shared values**

- **Get User Index**: inside a task keyword, returns the number of the virtual user, unique within the run.
- **Get User Iteration**: inside a task keyword, returns how many task runs this user has started.
- **Put Shared Value**: adds a value under a name for another user's step to take.
- **Take Shared Value**: takes the oldest value under a name, waiting up to a timeout for one.

**Run and check**

- **Run Load Test**: runs the scenario headless and waits until it ends. See [Run Load Test details](#run-load-test-details).
- **Get Locust Stats**: returns the stats of the last run: one row per request name, the total row and the fail ratio.
- **Get Aggregated Stats**: returns the total row of the last run.
- **Should Have No Failures**: fails if any request failed.
- **Should Meet Response Time**: fails if a percentile of one endpoint, or of all requests, is above a maximum.
- **Should Meet Throughput**: fails if requests per second over the run are below a minimum.
- **Should Meet Error Rate**: fails if the error rate is above a maximum, for all requests or one endpoint.

**Report**

- **Export Report**: writes the stats CSV and the Locust HTML report into the Robot output folder and links the report in the log.

**Web UI and distributed**

- **Start Locust Web**: starts the Locust web UI for a locustfile and returns at once. The UI has no login and no user limit.
- **Stop Locust Web**: stops the web UI that Start Locust Web started.
- **Run Distributed**: starts a master and its workers for a locustfile on this machine and returns at once.
- **Stop Distributed**: stops the master and the workers.

For the arguments of each keyword, see [keywords.html](keywords.html).

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
- `verify_tls=False` skips the TLS certificate check. `verify_tls` also
  takes the path of a CA bundle file, used to check the certificate. A path
  to a file that does not exist is refused.
- `proxy` is an `http://` proxy URL. Every http and https request of the
  run goes through it, except hosts in `no_proxy`. With an empty value, the
  library reads `HTTPS_PROXY` or `HTTP_PROXY` (either case) from the
  environment. `proxy=none` turns the proxy off, also the one from the
  environment.
- `no_proxy` is a comma list of host names that skip the proxy. A name
  also covers its subdomains, with or without a leading dot, so
  `example.com` and `.example.com` both cover `api.example.com`. A
  `host:port` entry covers only that port. When the
  proxy comes from the environment, the names in `NO_PROXY` are added.
- A second Create Load Test starts again from nothing: user classes, tasks,
  stages, stop rules and the stats of the last run are dropped.

### Run Load Test details

- `spawn_rate` is users started per second. `iterations` caps the task
  runs for all users together; `0` means no cap.
- The run is refused before it starts if the peak user count is above
  `max_users`. The peak is the users that really run: the highest stage
  user count, or `users` with no stages. See [Several user classes](#several-user-classes) and
  [Limits before the run](safety.md#limits-before-the-run).
- `stop_on_fail_ratio` sets the failure breaker: when the failure ratio goes
  over it, after `fail_ratio_warmup`, the run stops early. A breaker stop
  fails the keyword; `breaker_fails=False` lets it pass.
- When a `cpu` or `mem` stop rule ends the run, the keyword fails with
  `Inconclusive: the load machine ran out of room, ...`. The target was not
  judged. With `, stop as passed`, the run still passes.
- A load generator CPU over 90% logs a warning; `fail_on_busy_cpu=True`
  fails the keyword instead. After such a run, every Should keyword also
  logs a warning that the numbers may be skewed.
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

The `max_users` check counts only the users that really run: `users`, or
the highest stage user count with stages. The `fixed_count` values do not
add to it. See [Limits before the run](safety.md#limits-before-the-run).
Run Load Test does not refuse or clamp a `fixed_count` sum above that count;
it logs a warning. For example, with `users=2` and a class with
`fixed_count=5`, only 2 users run, fixed users first, and the check uses 2.

With stages, each stage caps the users. With a `1m:3` stage and a class
with `fixed_count=5`, at most 3 users run in that stage.

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
  `Cookie`, `Set-Cookie`, `X-Api-Key`, `Api-Key`, `X-Auth-Token` and
  `X-Access-Token` headers show as `***`. The `password`,
  `client_secret`, `access_token`, `refresh_token`, `id_token` and
  `otp` fields of JSON or form bodies also show as `***`. Query values
  with any of these names show as `***` too. Each `name=value` pair
  between `&` signs is checked on its own; a bare name with no `=`
  stays as written. The summary line of each call, with the request name
  and the failure text, is masked the same way. Other headers and the rest
  of the URL are logged as sent.
  To mask more names, give the library import argument `mask` a comma
  list of header or body field names, such as
  `Library    LocustLibrary    mask=X-Session, pin`. It applies to that
  library instance.
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
