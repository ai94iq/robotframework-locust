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

1. Build: Create Load Test starts a scenario for one host. The Add and Set
   keywords add users, tasks, waits, stages and stop rules to it.
2. Run: Run Load Test starts Locust headless in the Robot process and waits
   until the run ends. A stop rule or the failure breaker can end it early.
3. Check: the Should keywords read the stats of that run and fail the test
   when a number is out of bounds. They fail when the run recorded no
   requests.

## Keyword table

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
| Get User Index | | Inside a task keyword: the number of the virtual user running it, unique within the run. Use it for a unique value or data row per user. Python tasks read `user.index`. |
| Get User Iteration | | Inside a task keyword: how many task runs this user has started, counting this one. Python tasks read `user.iteration`. |
| Put Shared Value | name, value | Adds a value under a name for another user's step to take, such as an id one step created. |
| Take Shared Value | name, timeout=10s | Takes the oldest value under the name, waiting up to timeout for one. Each value goes to one taker. With none in time the keyword fails, so the task counts as a failure. Run Load Test starts with no values. |
| Set On Start | keyword_name | Sets the keyword each user runs when it starts. |
| Set On Stop | keyword_name | Sets the keyword each user runs when it stops. |
| Run Load Test | users=10, spawn_rate=1.0, run_time=30s, iterations=0, max_users=100, stop_on_fail_ratio=0, fail_ratio_warmup=10s | Runs the scenario headless. Refuses the run before it starts if the peak user count is above max_users (see [Several user classes](#several-user-classes) for the peak). iterations caps the task runs for all users together. The log gets a stats table per request name and the first 3 calls of each name plus up to 50 failed calls, in RequestsLibrary style. Values of the `Authorization`, `Proxy-Authorization`, `Cookie` and `Set-Cookie` headers, and the `password`, `client_secret`, `access_token`, `refresh_token`, `id_token` and `otp` fields of JSON or form bodies, show as `***`. URLs, query strings and other headers, such as `X-Api-Key`, are logged as sent. With verify_tls off, it logs one warning per host. With stop_on_fail_ratio set, the run stops early when failures pass it. |
| Get Locust Stats | none | Returns a dict with `rows` (a list of row dicts, one per request name), `aggregated` (one row dict, or None) and `fail_ratio` (a fraction from 0 to 1). Returns an empty dict before Run Load Test. |
| Get Aggregated Stats | none | Returns the aggregated row dict, or an empty dict before Run Load Test. |
| Should Have No Failures | none | Fails if any request failed. |
| Should Meet Response Time | endpoint, percentile, maximum | Fails if the percentile is above the maximum. Use an endpoint name, or `aggregated` for all requests. |
| Should Meet Throughput | minimum | Fails if requests per second is below the minimum. |
| Should Meet Error Rate | maximum, endpoint= | Fails if the error rate is above the maximum, such as `1%`. Checks all requests, or one endpoint. |
| Export Report | base_path=locust | Writes `<base>_stats.csv` and the Locust HTML report `<base>.html` into the Robot output folder, links the HTML report in the log, and returns the base path. |
| Start Locust Web | locustfile, port=8089 | Starts the Locust web UI for a locustfile (a path to an existing Python file) in a subprocess and returns at once. The UI is at `http://127.0.0.1:<port>`. A second call stops the first UI. |
| Stop Locust Web | none | Stops the web UI that Start Locust Web started. |
| Run Distributed | locustfile, processes=2 | Starts a master and `processes` workers for a locustfile on this machine and returns at once. The master binds to 127.0.0.1 only. A second call stops the first set. |
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

A stats row dict has the keys `name`, `request_count`, `failure_count`,
`median`, `average`, `min`, `max`, `p50`, `p90`, `p95`, `p99` and `p999`
(response times in milliseconds), and `rps` and `failures_s` (per second).

Start Locust Web and Run Distributed run your own locustfile in separate
Locust processes. The scenario that the Add and Set keywords build, the
`max_users` check, the host allowlist, stop rules, shared values and user
indexes do not apply to them, and the Should keywords do not read their
stats. Stop them with Stop Locust Web and Stop Distributed, which wait up to
10 seconds per process and then kill it.

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
example, Checker gets 2 users and Browser gets the other 18. The peak that `max_users` checks is the higher of
two numbers: the highest stage user count (or `users` when there are no
stages), and the sum of the `fixed_count` values. In the example above the
peak is 20, since 20 is higher than 2.

## Python tasks

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

Users of Run Load Test share one Robot process, so the library gives each task keyword its own
numbers through keywords, not variables:

- Get User Index returns the number of the user that runs the task. Use it to
  pick a unique data row or build a unique name.
- Get User Iteration returns how many task runs this user has started.

Python tasks read the same values as `user.index` and `user.iteration`.

One step can hand data to another step during a run. Put Shared Value adds a
value under a name. Take Shared Value takes the oldest value under that name,
and waits up to its timeout for one. Each value goes to one taker:

```robotframework
Create Order
    ${id}=    Create Order Through The Api
    Put Shared Value    order    ${id}

Pay Order
    ${id}=    Take Shared Value    order    timeout=10s
    Pay Order Through The Api    ${id}
```

Run Load Test starts with no shared values.

## Reports

Run Load Test writes to the Robot log:

- a stats table per request name,
- the first 3 calls of each name and up to 50 failed calls, in RequestsLibrary
  style. Values of the `Authorization`, `Proxy-Authorization`, `Cookie` and `Set-Cookie` headers, and the `password`, `client_secret`, `access_token`, `refresh_token`, `id_token` and `otp` fields of JSON or form bodies, show as `***`. URLs, query strings and other headers, such as `X-Api-Key`, are logged as sent.

Export Report writes `<base>_stats.csv` and the Locust HTML report
`<base>.html` beside `log.html`, and links the HTML report in the log.

## Environment variables

| Variable | What it does |
|---|---|
| `LOCUSTLIBRARY_ALLOWED_HOSTS` | Host allowlist, a comma list, when Create Load Test gets no `allowed_hosts`. |
| `LOCUSTLIBRARY_FEED` | A file that Run Load Test writes the live feed to, one JSON line per second. Locust Studio sets it for its own runs. |
