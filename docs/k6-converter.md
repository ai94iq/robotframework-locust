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
   `src/LocustLibrary/k6/options.py`). k6 runs only the script's init code.
   It sends no request, and the converter never calls `k6 run`.
2. The scanner (`src/LocustLibrary/k6/scan.py`) parses the script with
   tree-sitter and reads each exported function. It marks each function plain
   or hand port.
3. The emitter (`src/LocustLibrary/k6/emit.py`) maps what k6 and LocustLibrary
   share into Robot keywords. Every item it cannot map goes into the report.

The k6 binary must be on PATH. If it is not, the command stops with an error.
`-e KEY=VALUE` pairs go to `k6 inspect` in sorted order.

The command writes a project folder under `--out` (default `robot`). Each
file name starts with the script's file name without its extension, called the
stem here. Paths are relative to the project folder:

| File | Content |
|---|---|
| `tests/<stem>.robot` | Thin suite: one test, `<Title> Load - <Condition> - Thresholds Met`, that calls `Test <Title> Load` |
| `collections/<stem>_test_keywords.resource` | Build, Run and Check keywords. Threshold endpoints sit in `@{<STEM>_CHECK_<n>_ENDPOINTS}` lists, looped with FOR |
| `resources/resources.resource` | Entry file every suite imports. Rebuilt on each run: LocustLibrary, every tasks module, every collection |
| `resources/variables.resource` | `${ENV}`, default `dev`. Written only when missing |
| `resources/<env>_variables.resource` | `${HOST}` and `${PROXY}` for one environment (`--env-name`, default dev). Written only when missing |
| `resources/python/<stem>_tasks.py` | One function per exec function, imported as a library so Add Python Task finds it |
| `reports/<stem>.k6-report.md` | One row per item: status and note |

The condition in the test name describes the load, such as `Ramp To 20 Users`.

## Mapping table

| k6 | LocustLibrary | Report status |
|---|---|---|
| Scenario and its `exec` function | Add User Class with `weight` set to the peak VUs, then Add Python Task | mapped or hand port |
| `ramping-vus` stages, all scenarios | Set Load Stages, user counts summed per stage | approximate when stage timings differ |
| `constant-vus` | Run Load Test with users and run_time | mapped |
| `shared-iterations` | Run Load Test with users, run_time and iterations | mapped |
| `arrival-rate` and per-VU executors | Run Load Test with looping users | approximate |
| `insecureSkipTLSVerify` | Create Load Test with verify_tls=False | mapped |
| `sleep(number)` in an exec function | Set Wait Time, same value as minimum and maximum | mapped |
| `http_req_duration` p50, p90, p95, p99, p99.9 | Should Meet Response Time, per endpoint or aggregated | mapped |
| `http_req_failed` rate | Should Meet Error Rate, in percent, per endpoint | mapped |
| Any other threshold | none | unsupported |

Notes on the rows:

- Peak VUs are the highest stage target, else `vus`, else `maxVUs`. The weight
  is at least 1.
- Iterations are summed only when every scenario is `shared-iterations`.
  `constant-vus` scenarios get no iterations.
- run_time is the longest scenario duration. When no scenario sets one, the
  run is 600 s (`_load` in `emit.py`).
- A mix of executors that includes `ramping-vus`, or any other mix that is not
  only `constant-vus` and `shared-iterations`, uses the users path and is
  flagged approximate.
- Stage timings come from the first scenario. The report says so when another
  scenario uses different timings.
- The last `sleep` with a number in an exec function sets the wait time.
- A script with no thresholds gets `Should Have No Failures` in its Check
  keyword, and an approximate row in the report.
- A threshold keyed to an endpoint, such as `http_req_duration{endpoint:login}`,
  uses that endpoint name in the check.
- k6 writes a percentile as `p(99.9)`. The converter reads it as `p999`. Other
  percentiles, such as `p(75)`, and the `avg`, `med`, `min` and `max` stats on
  `http_req_duration` are unsupported.

## Plain and hand port functions

A function is plain when each of its statements is one of these:

- `http.get`, `http.post`, `http.put`, `http.patch` or `http.del` with a string
  URL. The body and params must be literals. A body wrapped in `JSON.stringify`
  around a literal counts too.
- `check()`. The check is skipped, so k6 checks are not converted.
- `sleep` with a number literal.
- A `const` or `let` that holds one of the calls above.

Any other statement makes the function a hand port. The report gives the first
line that stopped the scan. A call to another local function, such as
`tokenFlow()`, is a hand port for this reason. The generated stub looks like
this:

```python
def tokenScenario(user: Any) -> None:
    """Hand port from combined.js line 56: ..."""
    raise NotImplementedError("hand port: combined.js line 56")
```

A plain function becomes calls such as
`user.client.post(url, json={...}, headers={...}, name=...)`. The `name` is the
endpoint tag, or the URL when the call has no tag.

To port a function by hand, replace its stub in
`resources/python/<stem>_tasks.py` with the calls. Keep the request
name equal to the k6 endpoint tag. The threshold checks find a stats row by
that name, so a different name leaves the check with no row to read.

## Safety

- Users above `--max-users` (default 100) are cut to that number. The report
  gets a `clamped` row.
- `Run Load Test` gets `max_users=<value>` from `--max-users` and refuses a run
  whose peak exceeds it. To change the ceiling, rerun the converter with a new
  `--max-users`, or edit the `max_users=` argument in the Run keyword of
  `collections/<stem>_test_keywords.resource`.
- The converter sends no request and never runs a k6 load test.

## Limits

- A think time held in a variable is not a number literal. The function
  becomes a hand port at that line. The wait time stays 0s when no literal
  `sleep` is left. Set the wait time by hand.
- k6 thresholds are strict: `p(95)<800` fails at exactly 800 ms. The Robot check
  fails only above its maximum, so 800ms passes there. Use a maximum one
  millisecond lower if you need the same result.
- Only exported functions are scanned. An exec function that is not exported is
  a hand port, and the report says it was not found.
- The host is the first absolute URL in a plain call. When none is found, `${HOST}` in the
  environment file is `http://127.0.0.1` and the report says to set it by hand.
- Generated tasks raise `NotImplementedError` until ported.
- Arrival-rate and per-VU executors run as looping users, so the count is
  approximate.

## Example run

A run on a three-scenario sample, `combined.js`, produced this report. Each
scenario calls a local helper, so each is a hand port:

| Item | Status | Note |
|---|---|---|
| scenario otp | hand port | line 52: otpFlow() is not an HTTP call, check or sleep |
| scenario signup | hand port | line 47: signupFlow() is not an HTTP call, check or sleep |
| scenario token | hand port | line 57: tokenFlow() is not an HTTP call, check or sleep |
| threshold http_req_duration p95 | mapped | register |
| threshold http_req_duration p95 | mapped | token |
| threshold http_req_duration p95 | mapped | verify-phone |
| threshold http_req_failed rate | mapped | register |
| threshold http_req_failed rate | mapped | token |
| threshold http_req_failed rate | mapped | verify-phone |
| host | set by hand | no absolute URL found; HOST defaults to http://127.0.0.1 |

The suite is thin. Its one test calls the collection keyword:

```
*** Test Cases ***
Combined Load - Ramp To 20 Users - Thresholds Met
    [Documentation]    Runs the combined.js profile and passes when every converted check holds.
    Test Combined Load
```

The collection holds the steps. The Build keyword has one user class per
k6 scenario:

```
Build Combined Users
    Create Load Test    ${HOST}    verify_tls=${False}    proxy=${PROXY}
    Add User Class    otp    weight=6
    Set Wait Time    0s    0s
    Add Python Task    otpScenario    combined_tasks.otpScenario
    Add User Class    signup    weight=8
    Set Wait Time    0s    0s
    Add Python Task    signupScenario    combined_tasks.signupScenario
    Add User Class    token    weight=6
    Set Wait Time    0s    0s
    Add Python Task    tokenScenario    combined_tasks.tokenScenario

Run Combined Load
    Set Load Stages    120s:20    600s:20    60s:0
    Run Load Test    max_users=100

Check Combined Load
    FOR    ${endpoint}    IN    @{COMBINED_CHECK_1_ENDPOINTS}
        Should Meet Response Time    ${endpoint}    p95    1000ms
    END
    FOR    ${endpoint}    IN    @{COMBINED_CHECK_2_ENDPOINTS}
        Should Meet Error Rate    1%    endpoint=${endpoint}
    END
```

Port the three stubs in `resources/python/combined_tasks.py`, then run the
project from its folder with `robot -v ENV:dev robot/tests`.
