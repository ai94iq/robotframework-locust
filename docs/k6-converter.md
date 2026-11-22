# k6 converter

`rflocust-k6` reads a k6 script and writes a Robot project for LocustLibrary:
a thin suite, keyword collections, resources, a tasks module and a report. This
page covers how the conversion works, what it maps, and what you port by hand.

## Contents

- [How it works](#how-it-works)
- [Mapping table](#mapping-table)
- [Plain and hand port functions](#plain-and-hand-port-functions)
- [Safety](#safety)
- [Limits](#limits)
- [Example run](#example-run)

## How it works

1. The options reader runs `k6 inspect --execution-requirements` on the script
   and reads its resolved options: scenarios, thresholds, the TLS flag and the
   total duration. The call has a 60 s timeout (`run_inspect` in
   `src/LocustLibrary/k6/options.py`). k6 runs the script's init (top-level) code
   as you, so convert only scripts you trust (see [safety.md](safety.md)). The
   converter never calls `k6 run`. k6 gets only these environment variables:
   `PATH`, `SYSTEMROOT`, `HOME`, `USERPROFILE`, `TEMP`, `TMP` and `TMPDIR`, when
   set. `__ENV` in init code sees those and the `-e` pairs, nothing else.
2. The scanner (`src/LocustLibrary/k6/scan.py`) parses the script with
   tree-sitter and reads each exported function. It marks each function plain
   or hand port.
3. The emitter (`src/LocustLibrary/k6/emit.py`) maps what k6 and LocustLibrary
   share into Robot keywords. Every item it cannot map gets a report row, except
   the dropped iteration caps in a mixed run (see the mapping notes).
   `profile.py` maps scenarios and thresholds to keyword lines, and
   `robot_files.py` writes the suite, resources and Python tasks.

The k6 binary must be on PATH. If it is not, the command stops with a Python
traceback that ends in
`FileNotFoundError: k6 is not on PATH; k6 inspect is needed to read options`.
If `k6 inspect` exits non-zero or runs past 60 s, the command also stops with a
traceback (`CalledProcessError` or `TimeoutExpired`) and writes no files. The converter
checks no k6 version. Install k6 from https://grafana.com/docs/k6/latest/set-up/install-k6/.
`-e KEY=VALUE` pairs go to `k6 inspect` in sorted order.

The command writes a project folder under `--out` (default `robot`). Each
file name starts with the script's file name without its extension, called the
stem here. Paths are relative to the project folder:

| File | Content |
|---|---|
| `tests/<stem>.robot` | Thin suite: one test, `<Title> Load - <Condition> - Thresholds Met`, that calls `Test <Title> Load` |
| `collections/<stem>_test_keywords.resource` | Build, Run and Check keywords. Threshold endpoints sit in `@{<STEM>_CHECK_<n>_ENDPOINTS}` lists, looped with FOR |
| `resources/resources.resource` | Entry file every suite imports. Rebuilt on each run: LocustLibrary with `python_path` set to `resources/python`, then every collection |
| `resources/variables.resource` | `${ENV}`, default `dev`. Written only when missing |
| `resources/<env>_variables.resource` | `${HOST}` and `${PROXY}` for one environment (`--env-name`, default dev; letters, digits, `_`, `.` and `-` only). `${PROXY}` is `${EMPTY}`, which means no proxy. Written only when missing |
| `resources/python/<stem>_tasks.py` | One function per exec function. Add Python Task finds it through `python_path` |
| `reports/<stem>.k6-report.md` | One row per item: status and note |

The condition in the test name describes the load, such as `Ramp To 20 Users`.
The name does not mean every k6 threshold was checked. Unsupported thresholds
are left out; the report lists them.

Each run overwrites the suite, the collection, the tasks module and the report
for the script, and rebuilds `resources.resource`. Hand ports in
`resources/python/<stem>_tasks.py` and edits to the collection are lost on a
rerun. Copy them out first, or rerun with a different `--out`. Only the two
variables files are kept.

## Mapping table

k6 terms used below: a scenario is one named workload, and its `exec` function
is the code each virtual user (VU) runs. An executor sets how a scenario
schedules VUs. A threshold is a pass rule on a metric. Init code is the
script's top-level code. See the k6 docs at https://grafana.com/docs/k6/latest/.

| k6 | LocustLibrary | Report status |
|---|---|---|
| Scenario and its `exec` function | Add User Class with `weight` set to the peak VUs, then Add Python Task | mapped or hand port |
| `ramping-vus` stages, when every scenario is `ramping-vus` | Set Load Stages, user counts summed per stage | approximate when stage timings differ |
| `constant-vus` | Run Load Test with users, spawn_rate and run_time | mapped, in an `executors` row |
| `shared-iterations` | Run Load Test with users, run_time and iterations | mapped, in an `executors` row |
| `arrival-rate` and per-VU executors | Run Load Test with looping users (users that repeat their tasks with no fixed count) | approximate |
| `insecureSkipTLSVerify` | Create Load Test with verify_tls=False | mapped |
| `sleep(number)` in an exec function | Set Wait Time from the last `sleep`, same value as minimum and maximum | mapped |
| `http_req_duration` p50, p90, p95, p99, p99.9 | Should Meet Response Time, per endpoint or aggregated | mapped |
| `http_req_failed` rate | Should Meet Error Rate, in percent, per endpoint | mapped; approximate for a strict `<` limit |
| Any other threshold | none | unsupported |

Report statuses:

- mapped: the item became a keyword with the same meaning.
- approximate: the item became a keyword that runs close to, not exactly like,
  k6. The note says what differs. Check that the run still fits your need.
- hand port: the converter wrote a stub. Write the Python yourself.
- unsupported: the item was left out. Add a check by hand if you need it.
- clamped: the user count was cut to `--max-users`. Raise the ceiling if you
  need the full load.
- set by hand: edit the value the note names.

Notes on the rows:

- For non-staged runs, users is the sum of every scenario's peak VUs, and
  spawn_rate equals users, so all users start at once. Locust splits users
  across classes by weight, so each scenario's count is close to its peak VUs,
  not exact.

- Peak VUs are the highest stage target, else `vus`, else `maxVUs`. The weight
  is at least 1.
- Iterations are summed only when every scenario is `shared-iterations`.
  `constant-vus` scenarios get no iterations. In a mix of `constant-vus` and
  `shared-iterations`, the iteration caps are dropped. The `executors` row is still
  mapped and does not say so. The run then stops on run_time alone: the summed peak VUs run for
  the longest scenario duration, or 600 s (`load` in `profile.py`).
- run_time is the longest scenario duration. When no scenario sets one, the
  run is 600 s (`load` in `profile.py`).
- A mix of executors that includes `ramping-vus`, or any other mix that is not
  only `constant-vus` and `shared-iterations`, uses the users path (Add User Class with Run Load Test
  users=, not Set Load Stages) and is flagged approximate.
- Stage timings come from the first scenario. The report says so when another
  scenario uses different timings.
- The last `sleep` in an exec function sets the wait time. Earlier sleeps with
  other values are dropped, and the report has no row for that.
- A script with no thresholds gets `Should Have No Failures` in its Check
  keyword, and an approximate row in the report.
- A threshold keyed to an endpoint, such as `http_req_duration{endpoint:login}`,
  uses that endpoint name in the check.
- k6 writes a percentile as `p(99.9)`. The converter reads it as `p999`. Other
  percentiles, such as `p(75)`, and the `avg`, `med`, `min` and `max` stats on
  `http_req_duration` are unsupported.

## Plain and hand port functions

A function is plain when it holds only simple HTTP calls (`http.get`,
`http.post` and the like, with a string URL and literal body and params),
`check()` calls and `sleep` calls. These become Python calls and a wait time.
`check()` is skipped, so k6 checks are not converted. A `sleep` that reads
`Number(__ENV.X || n)` from a top-level `const` uses its default `n`; a
`-e X=...` value does not change it.

A call to a local function with no arguments, such as `tokenFlow()`, does not
stop the scan. The HTTP calls around it still convert. The helper itself is not
converted: the report gets a row `helper tokenFlow | hand port | combined.js
line 57: tokenFlow() is not converted`. Port the helper's calls by hand.

Any other statement makes the function a hand port, including a call to a local
function with arguments, such as `tokenFlow(user)`. The report gives the first
line that stopped the scan. The generated stub looks like this:

```python
def tokenScenario(user: Any) -> None:
    'Hand port from combined.js line 56: line 57: tokenFlow(user) is not an HTTP call, check or sleep.'
    raise NotImplementedError('hand port: combined.js line 56')
```

The first line number is where the function starts. The second is the
statement that stopped the scan, the same line the report shows.

A plain function becomes calls such as
`user.client.post(url, json={...}, headers={...}, name=...)`. The `name` is the
endpoint tag, or the URL when the call has no tag. A k6 call sets the tag in
its params, for example
`http.post(url, body, { tags: { endpoint: 'login' } })`. Here the Robot
request name is `login`.

To port a function by hand, replace its stub in
`resources/python/<stem>_tasks.py` with the calls. Keep the request
name equal to the k6 endpoint tag. The threshold checks find a stats row by
that name, so a different name leaves the check with no row to read.

## Safety

- `--max-users` (default 100) caps the load. When every scenario is
  ramping-vus (the staged path), each stage target is multiplied by
  `max-users / peak` and rounded, so the ramp keeps its shape at a lower
  height. On every other path (constant-vus, shared-iterations or a mix), the
  total user count is cut to `max-users`. Both keep the peak at or below the
  ceiling; scaling is used only where there are stages whose shape can be kept. Both write a `clamped` row to the
  report.
- Run Load Test gets `max_users=<value>` from `--max-users` and refuses a run
  whose peak exceeds it. To change the ceiling, rerun the converter with a new
  `--max-users`, or edit the `max_users=` argument in the Run keyword of
  `collections/<stem>_test_keywords.resource`.
- The init-code warning is in [safety.md](safety.md).

## Limits

- A think time held in any other variable, such as one declared inside the
  function, is not read. The function becomes a hand port at that line. The
  wait time stays 0s when no readable `sleep` is left. Set the wait time by
  hand.
- k6 `<` thresholds are strict: `p(95)<800` fails at exactly 800 ms. The Robot
  check fails only above its maximum. Locust percentiles are whole
  milliseconds, so the converter writes a strict response time limit one
  millisecond lower: `p(95)<800` becomes `799ms`. `<=` keeps its limit.
- A strict error rate, such as `rate<0.01`, keeps its limit (1%), so the check
  also passes at exactly 1%. The report adds an approximate row that says so.
- Only exported functions are scanned. An exec function that is not exported is
  a hand port, and the report says it was not found.
- The host is the first absolute URL in any HTTP call the scanner read, in
  any exported exec function, hand port or not. A call after the statement
  that made a function a hand port counts too. When none is found, `${HOST}` in the
  environment file is `http://127.0.0.1` and the report says to set it by hand.
- Generated tasks raise `NotImplementedError` until ported.
- Arrival-rate and per-VU executors run as looping users, so the count is
  approximate.

## Example run

A run on a three-scenario sample, `combined.js`, produced this report. Each
scenario calls a local helper with no arguments. The helper rows below follow
from the code as it is now (scenario and helper rows edited by hand, not from a
new run):

The Note column names the endpoint of each threshold row.

| Item | Status | Note |
|---|---|---|
| scenario otp | mapped | 0 HTTP calls |
| helper otpFlow | hand port | combined.js line 52: otpFlow() is not converted |
| scenario signup | mapped | 0 HTTP calls |
| helper signupFlow | hand port | combined.js line 47: signupFlow() is not converted |
| scenario token | mapped | 0 HTTP calls |
| helper tokenFlow | hand port | combined.js line 57: tokenFlow() is not converted |
| threshold http_req_duration p95 | mapped | endpoint register |
| threshold http_req_duration p95 | mapped | endpoint token |
| threshold http_req_duration p95 | mapped | endpoint verify-phone |
| threshold http_req_failed rate | mapped | endpoint register |
| threshold http_req_failed rate | mapped | endpoint token |
| threshold http_req_failed rate | mapped | endpoint verify-phone |
| host | set by hand | no absolute URL found; HOST defaults to http://127.0.0.1 |

The suite is thin. Its one test calls the collection keyword:

```
*** Test Cases ***
Combined Load - Ramp To 20 Users - Thresholds Met
    [Documentation]    Runs the combined.js profile and passes when every converted check holds.
    Test Combined Load
```

The collection holds the Build, Run and Check keywords. Its Run keyword:

```
Run Combined Load
    Set Load Stages    120s:20    600s:20    60s:0
    Run Load Test    max_users=100
    Export Report    combined
```

Port the three stubs in `robot/resources/python/combined_tasks.py`. Then, from
the folder that holds `robot` (where you ran the converter), run
`robot -v ENV:dev robot/tests`.
