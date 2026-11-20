# Changelog

## 0.1.0 (unreleased)

- Add User Class starts a user class with its own tasks, wait time, weight and
  fixed user count. One class maps to one k6 scenario. (b01685d)
- Set Load Stages ramps users over `duration:users` stages, moving linearly.
  Run Load Test takes `iterations`, a task budget shared by all users. (5e62482)
- Create Load Test takes `verify_tls` and `proxy`. The proxy goes straight to
  the client, because Locust ignores HTTPS_PROXY. Should Meet Error Rate takes
  an endpoint name. (973f485)
- Add Python Task calls a `module.function` with the Locust user, so each
  request in a flow gets its own stats row. (7b7b003)
- Add Get Request and Add Post Request take headers, a JSON or form body, and
  `expected_status` (one code, a comma list or a list; default 200). Only the
  listed codes pass. Before, Locust's default (4xx and 5xx fail) applied.
  (be353d3)
- Run Load Test takes `max_users` (default 100). A run whose peak user count
  is above it is refused before Locust starts. (044f1cb)
- k6 options reader runs `k6 inspect` with a 60 s timeout and reads the
  resolved scenarios, thresholds and TLS flag. It never runs `k6 run`.
  (174007f)
- k6 scanner finds the exported functions in a k6 script and marks each one
  plain or hand port, with the first line that stops it. (e5f8509)
- k6 emitter writes a Robot suite, a tasks module and a report from the
  options and the scan. (3baa9b6)
- rflocust-k6 command converts one k6 script into those three files.
  `--max-users` sets the user ceiling, default 100. (d4c1740)
- The first Add User Class replaces the empty default user class. (9944a54)
- rflocust-k6 writes a project folder in the four-layer house layout instead of
  the three files from d4c1740: a thin suite in tests/, keyword collections, one
  entry resource, an ENV switch with per-environment variables, tasks under
  resources/python/ and the report. Threshold endpoints run in a FOR loop. A
  script with no thresholds gets Should Have No Failures. New --env-name flag,
  default dev. The output passes robot --dryrun and Robocop 9.4. (10edca0)
- LocustLibrary takes a `python_path` import argument, a folder searched for
  Add Python Task modules. The k6 entry resource uses it instead of importing
  each tasks module as a library, which logged a "contains no keywords" warning
  per module.
