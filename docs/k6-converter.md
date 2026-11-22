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

1. The options reader first reads `export const options` straight from the
   script, when every value in it is a literal (`static_options` in
   `src/LocustLibrary/k6/scan.py`). This runs no k6 and needs no
   `--trust-script`. The report row is `options | read statically`.
   When an option is computed, the reader falls back to
   `k6 inspect --execution-requirements`, which gives the resolved options:
   scenarios, thresholds, the TLS flag and the total duration. The call has a
   60 s timeout (`run_inspect` in `src/LocustLibrary/k6/options.py`). k6 runs
   the script's init (top-level) code as you, so convert only scripts you trust
   (see [safety.md](safety.md)). The fallback runs only when you pass
   `--trust-script`. Without it, the command exits 1 with a one-line reason
   that names the option that is not a literal, and writes no files. The report
   row is then `options | from k6 inspect`. The converter never calls `k6 run`. k6 gets only these environment variables:
   `PATH`, `SYSTEMROOT`, `HOME`, `USERPROFILE`, `TEMP`, `TMP` and `TMPDIR`, when
   set. `__ENV` in init code sees those and the `-e` pairs, nothing else.
2. The scanner (`src/LocustLibrary/k6/scan.py`) parses the script with
   tree-sitter and reads each exported function. It marks each function plain
   (converted to Python calls) or hand port (you write it). See
   [Plain and hand port functions](#plain-and-hand-port-functions).
3. The emitter (`src/LocustLibrary/k6/emit.py`) maps what k6 and LocustLibrary
   share into Robot keywords. Every item it cannot map exactly gets a report row.
   `profile.py` maps scenarios and thresholds to keyword lines, and
   `robot_files.py` writes the suite, resources and Python tasks.

A script path that does not exist stops the command with
`rflocust-k6: no such file: <path>`.

Options: `--trust-script` (needed only for computed options), `--out`, `--max-users`, `--env-name`,
`-e KEY=VALUE`, `--host` and `--force` (see below).

The k6 binary must be on PATH when the fallback runs. If it is not, the command stops with a Python
traceback, not a one-line error (see [Limits](#limits)). The traceback ends in
`FileNotFoundError: k6 is not on PATH; k6 inspect is needed to read options`.
If `k6 inspect` exits non-zero or runs past 60 s, the command also stops with a
traceback (`CalledProcessError` or `TimeoutExpired`) and writes no files. The converter
checks no k6 version. Install k6 from https://grafana.com/docs/k6/latest/set-up/install-k6/.
`-e KEY=VALUE` pairs go to `k6 inspect` in sorted order.

The command writes a project folder under `--out` (default `robot`). Each
file name starts with the script's file name without its extension, called the
stem here. The script file name may hold only letters, digits, `_`, `.` and
`-`. Any other name stops the command with `unsupported script name`, and no
files are written. Paths are relative to the project folder:

| File | Content |
|---|---|
| `tests/<stem>.robot` | Thin suite: one test, `<Title> Load - <Condition> - Mapped Thresholds Met`, that calls `Test <Title> Load` |
| `collections/<stem>_test_keywords.resource` | Build, Run and Check keywords. Threshold endpoints sit in `@{<STEM>_CHECK_<n>_ENDPOINTS}` lists, looped with FOR |
| `resources/resources.resource` | Entry file every suite imports. Rebuilt on each run: LocustLibrary with `python_path` set to `resources/python`, then every collection |
| `resources/variables.resource` | `${ENV}`, default `dev`. Written only when missing |
| `resources/<env>_variables.resource` | `${HOST}`, `${ALLOWED_HOSTS}`, `${PROXY}` and `${ALLOW_STUBS}` for one environment (`--env-name`, default dev; letters, digits, `_`, `.` and `-` only). `${ALLOWED_HOSTS}` starts as the host name of `${HOST}`; the two are not linked, so when you change `${HOST}`, change `${ALLOWED_HOSTS}` too. `${PROXY}` is `${EMPTY}`, which reads `HTTPS_PROXY` or `HTTP_PROXY` from the environment; set it to `none` for no proxy. `${ALLOW_STUBS}` is `${False}` (see [Plain and hand port functions](#plain-and-hand-port-functions)). Written only when missing; a kept file without `${ALLOW_STUBS}` gets the line appended, with the row `env file | updated`; on a rerun, `--host` rewrites only its `${HOST}` and `${ALLOWED_HOSTS}` lines |
| `resources/python/<stem>_tasks.py` | One function per exec function. Add Python Task finds it through `python_path`. Kept when it exists, unless you pass `--force`, which first copies it to `<stem>_tasks.py.bak` (or `.bak.1`, `.bak.2` and so on when taken) |
| `reports/<stem>.k6-report.md` | One row per item: status and note |

`<Title>` is the stem in title case, with `_` read as a space, such as `Combined` for `combined.js`.
The condition in the test name describes the load, such as `Ramp To 20 Users`.
"Mapped Thresholds Met" means only the converted checks passed, not every k6
threshold. Unsupported thresholds are left out; the report lists them. With no
converted threshold, the only check is `Should Have No Failures`.

Each run rewrites the suite, the collection and the report for the script, and
rebuilds `resources.resource`. Edits to the collection are lost on a rerun.
The tasks module is kept when it exists, so your hand ports survive. The report
then gets a row `tasks file | kept`. When the kept file lacks a function the
suite calls, the report also gets a row `tasks file | missing` that names each
one. The kept file must define one function per exec function. Pass `--force`
to rewrite the tasks module. The old file is copied to `<stem>_tasks.py.bak`
first, and the report gets a row `tasks file | backed up` that names the
backup. When that name is taken, the copy goes to `.bak.1`, then `.bak.2`
and so on; no backup is overwritten. When the old file already equals the new
text, nothing is copied.
The two variables files are also kept.

## Mapping table

k6 terms used below: a scenario is one named workload, and its `exec` function
is the code each virtual user (VU) runs. An executor sets how a scenario
schedules VUs. A threshold is a pass rule on a metric. Init code is the
script's top-level code. See the k6 docs at https://grafana.com/docs/k6/latest/.

Top-level `vus`, `iterations`, `duration` and `stages` become one scenario
named `default`, as k6 does it. `vus` alone becomes `shared-iterations` with
`vus` users and the same number of iterations. `stages` becomes `ramping-vus`,
with `vus` as the start count. `iterations` with `duration` becomes
`shared-iterations` with `duration` as its `maxDuration`. These shortcuts
replace any `scenarios`. The converter refuses `iterations` or `duration`
together with `stages` or `scenarios`, and `stages` together with
`scenarios`, as k6 does.

| k6 | LocustLibrary | Report status |
|---|---|---|
| Scenario and its `exec` function | Add User Class with `weight` set to the peak VUs, then Add Python Task | mapped or hand port |
| `ramping-vus` stages, when every scenario is `ramping-vus` | Set Load Stages, user counts summed per stage | approximate when stage timings differ |
| `constant-vus` | Run Load Test with users, spawn_rate and run_time | mapped, in the `executors` row; approximate when mixed with `shared-iterations` |
| `shared-iterations` | Run Load Test with users, run_time and iterations | mapped, in the `executors` row; approximate when mixed with `constant-vus` |
| Any other executor, such as `per-vu-iterations`, `constant-arrival-rate` and `ramping-arrival-rate` | Run Load Test with looping users | approximate, in the `executors` row |
| `insecureSkipTLSVerify` | Create Load Test with verify_tls=False | mapped |
| `sleep(number)` in an exec function | Set Wait Time from the last `sleep`, same value as minimum and maximum | mapped; approximate when the function has more than one `sleep` |
| `check(r, { ...: (r) => r.status === N })` | Expected status on the call before it; any other status fails the request | mapped |
| Any other `check()` | none | unsupported, one `check <name>` row each |
| `http_req_duration` p50, p90, p95, p99, p99.9 | Should Meet Response Time, per endpoint or aggregated | mapped |
| `http_req_failed` rate | Should Meet Error Rate, in percent, per endpoint | mapped; approximate for a strict `<` limit |

The report has one row named `executors` that lists the executors of all
scenarios and how they run. Looping users are users that repeat their tasks
until run_time ends, with no iteration cap.
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
  `shared-iterations`, the iteration caps are dropped, and the run stops on
  run_time alone (see the next note). The report then says
  `executors | approximate` and names the total of the dropped caps
  (`load` in `profile.py`). Only runs where every scenario uses the same one
  of these two executors are `mapped`.
- run_time is the longest scenario duration. When no scenario sets one, the
  run is 600 s (`load` in `profile.py`).
- Any mix of executors other than only `constant-vus` and `shared-iterations`
  uses the users path (Add User Class with Run Load Test users=, not Set Load
  Stages) and is flagged approximate.
- Stage timings come from the first scenario by name (scenarios are sorted by
  name). The report says so when another
  scenario uses different timings.
- The last `sleep` in an exec function sets the wait time. When the function
  has more than one `sleep`, the report adds a row
  `sleep <exec> | approximate | only the last sleep (Ns) is used`.
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
A call with no status check fails on a status of 400 or more, as Locust does by
default, which matches k6. A check of the form `r.status === N` sets the expected status of the HTTP call
just before it. The task then fails that request on any other status. Other
checks are not converted; each gets a `check <name> | unsupported` row.

A call to a local function with no arguments, such as `warmUp()`, does not
stop the scan. The HTTP calls around it still convert. The helper itself is not
converted: the report gets a row `helper warmUp | hand port | combined.js
line 45: warmUp() is not converted`. No stub is written for the helper. Add its
HTTP calls by hand to the generated function of the exec function that calls
it, at the point of the call.

Any other statement makes the function a hand port, including a call to a local
function with arguments, such as `tokenFlow('sample')`. The report gives the
first line that stopped the scan. The generated stub for
[samples/k6/combined.js](../samples/k6/combined.js) looks like this:

```python
def tokenScenario(user: Any) -> None:
    "Hand port from combined.js line 56: line 57: tokenFlow('sample') is not an HTTP call, check or sleep."
    from locust.exception import StopUser
    error = NotImplementedError('hand port: combined.js line 56')
    user.environment.events.request.fire(request_type='HAND PORT', name='tokenScenario',
                                         response_time=0, response_length=0,
                                         exception=error, context={})
    raise StopUser
```

The converter marks each stub with `tokenScenario.__hand_port__ = True`. The
Run keyword calls `check_hand_ports` (`src/LocustLibrary/k6/stubs.py`) before
the load starts. While a marked stub remains, the test fails with
`hand-port stubs not ported: tokenScenario; set ALLOW_STUBS to True to run anyway`.
Port the stub and remove its marker line. To run with stubs anyway, set
`${ALLOW_STUBS}` to `${True}` in the environment file.

With `${ALLOW_STUBS}` True, the stub records one failed `HAND PORT` request named after the function, then
stops that user. So `Should` checks and the fail ratio count the missing port as
a failure. That user sends no more load for the rest of the run, so the
scenario's load is gone. The run still ends on run_time. Port every stub
before you trust a run.

The first line number is where the function starts. The second is the
statement that stopped the scan, the same line the report shows.

A plain function becomes calls such as
`user.client.post(url, json={...}, headers={...}, name=...)`. A GET becomes
`user.client.get(url, name=...)`, and a string body becomes `data='...'` in
place of `json=`. A call with a status check is wrapped in
`with user.client.<verb>(..., catch_response=True) as response:`. The `name` is the
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
  `--max-users / peak` and rounded to the nearest whole number, so the ramp
  keeps its shape at a lower height. A target above 0 keeps at least 1 user;
  a target of 0 stays 0.
  On every other path (constant-vus, shared-iterations or a mix), the total
  user count is cut to `--max-users`. Both keep the peak at or below the
  ceiling, and both write a `clamped` row to the report.
- Run Load Test gets `max_users=<value>` from `--max-users` and refuses a run
  whose users exceed it. It counts the users that really run: the highest stage
  target, else `users`. A sum of `fixed_count` values above that only warns. To change the ceiling, rerun the converter with a new
  `--max-users`, or edit the `max_users=` argument in the Run keyword of
  `collections/<stem>_test_keywords.resource`. A hand edit is lost on the next
  conversion, so pass `--max-users` on each rerun.
- The suites it writes set these limits by default. Create Load Test gets
  `allowed_hosts=${ALLOWED_HOSTS}`. Create Load Test checks `${HOST}` against
  it once, before the run. It does not check each request: an absolute URL in
  the tasks module, a redirect or a hand-ported call can reach another host.
  The `host | detected` row names one origin only, so check the script for
  others.
  The Run keyword adds `Add Stop Rule    fail > 10% for 30s` and
  `Add Stop Rule    idle > 30s`, and Run Load Test gets
  `stop_on_fail_ratio=20%`. A stop rule or the fail ratio that ends the run
  fails the test. The report has a `safety | default` row.
- The init-code warning is in [safety.md](safety.md).

## Limits

- A think time held in any other variable, such as one declared inside the
  function, is not read. The function becomes a hand port at that line. The
  wait time stays 0s when no readable `sleep` is left. Set the wait time by
  hand.
- A `sleep` that reads `Number(__ENV.X || n)` from a top-level `const` always
  uses its default `n`. A `-e X=...` value does not change the wait time.
- k6 `<` thresholds are strict: `p(95)<800` fails at exactly 800 ms. The Robot
  check fails only above its maximum. Locust percentiles are whole
  milliseconds, so the converter writes a strict response time limit one
  millisecond lower: `p(95)<800` becomes `799ms`. `<=` keeps its limit.
- A strict error rate, such as `rate<0.01`, keeps its limit (1%), so the check
  also passes at exactly 1%. The report adds an approximate row that says so.
- Only exported functions are scanned. An exec function that is not exported is
  a hand port, and the report says it was not found.
- The host is the most common origin among the HTTP calls the scanner read, in
  any exported exec function, hand port or not. A tie goes to the origin seen
  first. The report row is `host | detected`. `--host http(s)://host[:port]`
  overrides it, with the row `host | set by --host`. On a rerun that keeps an
  existing environment file, `--host` rewrites only the `${HOST}` and
  `${ALLOWED_HOSTS}` lines of that file and leaves the rest. When the file has
  neither line, the report says `host | not applied`; set them by hand. When no origin is found,
  `${HOST}` is `http://127.0.0.1` and the report says to set it by hand.
- The suite refuses to start while a hand port stub remains, unless
  `${ALLOW_STUBS}` is True. Then each stub records a failed `HAND PORT` request.
- Executors other than `ramping-vus`, `constant-vus` and `shared-iterations`
  run as looping users, so the count is approximate.
- When the fallback runs, a missing k6, a failed `k6 inspect` or a 60 s timeout
  ends the command with a Python traceback, not a one-line error.

## Example run

[samples/k6/combined.js](../samples/k6/combined.js) has three scenarios
(`signup` is ramping-vus, `login` is constant-vus and `token` is
shared-iterations), endpoint tags, four
thresholds (one strict `<`, one unsupported `avg`), a helper called with no
arguments and a helper called with an argument. Every URL is on
`http://127.0.0.1:8765`. One call checks `r.status === 201`.
Its options are literal, so `rflocust-k6 samples/k6/combined.js --force --out <folder>`
needs no `--trust-script`. It wrote this report into a new folder:

| Item | Status | Note |
|---|---|---|
| executors | approximate | constant-vus, ramping-vus, shared-iterations run as 17 looping users; Locust has no arrival rate |
| threshold http_req_duration p95 | mapped | login |
| threshold http_req_duration p95 | mapped | register |
| threshold http_req_duration avg | unsupported | no LocustLibrary check for this metric |
| threshold http_req_failed rate | mapped | login |
| scenario login | mapped | 1 HTTP calls |
| scenario signup | mapped | 1 HTTP calls |
| helper warmUp | hand port | combined.js line 45: warmUp() is not converted |
| scenario token | hand port | line 57: tokenFlow('sample') is not an HTTP call, check or sleep |
| host | detected | http://127.0.0.1:8765: most common origin, 2 of 2 calls |
| safety | default | allowed_hosts=127.0.0.1; stop rules: fail > 10% for 30s; idle > 30s; stop_on_fail_ratio=20% |
| options | read statically |

The suite is thin. Its one test calls the collection keyword:

```
*** Test Cases ***
Combined Load - 17 Users For 90s - Mapped Thresholds Met
    [Documentation]    Runs the combined.js profile and passes when every converted check holds.
    Test Combined Load
```

The collection holds the Build, Run and Check keywords. Its Run keyword:

```
Run Combined Load
    [Documentation]    Runs the converted k6 load profile headless.
    ${allow}=    Get Variable Value    ${ALLOW_STUBS}    ${False}
    Evaluate    __import__('LocustLibrary.k6.stubs', fromlist=['_']).check_hand_ports('combined_tasks', $allow)
    Add Stop Rule    fail > 10% for 30s
    Add Stop Rule    idle > 30s
    Run Load Test    users=17    spawn_rate=17    run_time=90s    max_users=100    stop_on_fail_ratio=20%
    Export Report    combined
```

Port the `tokenScenario` stub in `resources/python/combined_tasks.py`, and add
the `warmUp` helper's calls to the function of the exec function that calls it. Remove the
`tokenScenario.__hand_port__ = True` line. Then, from the output folder, run
`robot -v ENV:dev tests`.
