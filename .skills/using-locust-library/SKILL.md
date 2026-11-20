---
name: using-locust-library
description: Writes, runs and checks Robot Framework load suites with LocustLibrary (robotframework-locust), Locust Studio and rflocust-k6. Use for "load test this API", "write a Locust suite", "convert this k6 script", "stop rule", "max_users".
---

# Using the Locust library

LocustLibrary builds and runs Locust load tests from a Robot suite. Full
guide: `docs/library.md`. Keyword reference: `docs/keywords.html`.

## Hard rules

1. Never run load against a host the user did not name for load. Ask first.
   A production host needs the user's explicit yes in the current message.
2. Every suite sets `allowed_hosts` on Create Load Test to the one host it
   tests.
3. Every suite has at least one stop rule, such as
   `Add Stop Rule    fail > 50% for 5s`, and passes `max_users` on Run
   Load Test. Do not raise `max_users` above 100 unless the user asked for
   that number.
4. A first run is small: 1 to 5 users for 30 s or less. Scale up only after
   it passes and the user agrees.
5. Never put a token or password in a suite. Read it from an environment
   variable (`%{API_TOKEN}`) or a variables file the user keeps.
6. Use `expected_text` on requests whose body proves success, so a 200 with
   an error page fails.

## Write a suite

Copy this shape and change the host, requests and limits:

```robotframework
*** Settings ***
Library    LocustLibrary

*** Test Cases ***
Items Under Load
    Create Load Test    ${HOST}    allowed_hosts=${HOST_NAME}
    Add Stop Rule    fail > 50% for 5s
    Add Stop Rule    p95 > 2s for 10s
    Set Wait Time    1s    2s
    Add Get Request    items    /items    expected_text="id"
    Set Load Stages    30s:5    1m:5    10s:0
    Run Load Test    max_users=10
    Should Have No Failures
    Should Meet Response Time    aggregated    p95    800ms
    Export Report    items
```

- Several kinds of user: Add User Class, then that class's tasks.
- A fixed rate per user: Set Pacing instead of Set Wait Time.
- Logic a request keyword cannot express: Add Python Task with
  `Library    LocustLibrary    python_path=${CURDIR}/python`.
- Unique data per user: Get User Index. Data one step makes for another:
  Put Shared Value and Take Shared Value.
- Log in once per user: Set On Start with a Python keyword that calls
  `LocustLibrary.users.current_user().client.post(...)`. Each user keeps
  its own cookies, so the later tasks run logged in.

Time values take `500ms`, `30s`, `2m`, `1h`. Percentiles take `50`,
`90`, `95`, `99` or `999`, with or without `p`.

## Run and read the result

```
robot --outputdir results items_load.robot
```

Read the result from `results/output.xml` or the console, never from memory:
the test status, the stats table Run Load Test logs, and any stop-rule
warning. Report the numbers with the run they came from. A stopped run says
which rule stopped it.

## Convert a k6 script

```
rflocust-k6 script.js --out robot --max-users 10
```

`k6 inspect` runs the script's init code, so convert only a script the user
trusts. Then read `robot/reports/<name>.k6-report.md`. Every `hand port`
row is a Python task that raises `NotImplementedError`. Port those before a
run, or tell the user which ones are left. Mapping: `docs/k6-converter.md`.

## Studio

`locust-studio` opens a desktop window for a person. An agent runs suites
with `robot`, not Studio.

## Limits reference

Only when a run is refused or stops early: read `docs/safety.md`.
