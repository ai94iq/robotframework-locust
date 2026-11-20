# Changelog

## 0.1.0 (unreleased)

- The Locust HTML report from Export Report now has its charts. Run Load Test
  starts Locust's per-second history recorder, which only Locust's own command
  line started before, so the charts were empty.
- The log's stats table looks like the table in Locust's HTML report: white
  card, Roboto 14px, 16px cells, light row lines, failures in red. It uses
  the columns of Locust's statistics table and adds
  Average, Min and Failures/s. Stats rows now carry the real failures per
  second instead of 0.
- Each logged call shows the time it was sent and the full URL on the
  response line, and long headers and bodies wrap.
- Run Load Test logs a stats table per request name instead of the raw stats
  line. It also logs the first 3 calls of each request name and up to 50
  failed calls, in RequestsLibrary style: request and response URL, headers
  and body, each in a block that opens on click. Passwords, client secrets,
  tokens, OTP fields and auth or cookie headers show as `***`. Bodies are cut
  at 10,000 characters.
- With verify_tls off, the run logs one warning per host instead of one
  urllib3 warning per call.
- Export Report writes into the Robot output folder, next to log.html. It now
  also writes the Locust HTML report as `<base>.html` and links it in the log.
- rflocust-k6 adds Export Report after Run Load Test in every generated suite.
- Run Load Test no longer takes `csv_prefix`. It was stored but never used;
  Export Report writes the files.
- rflocust-k6 passes the host and environment name through `robot.utils.escape`
  when it writes the variables file. The host check already refuses Robot
  syntax; this is a second guard.
- rflocust-k6 reads `sleep(THINK)` when THINK is a top-level number constant
  or `Number(__ENV.X || n)`. The wait time is the default `n`. Before, the
  function became a hand port and the wait time was 0s.
- Write Stats CSV puts an apostrophe before a name that starts with =, +, -,
  @, tab or CR, so a spreadsheet shows it as text and doesn't run it.
- Should Meet Response Time and Should Meet Error Rate check every row with the
  endpoint name. Before, only the first method was checked, so a slow or
  failing second method passed. Response time uses the slowest method. Error
  rate counts all methods together, as k6 does.
- k6 inspect gets only PATH, the temp and home folders and SYSTEMROOT from the
  environment. Init code can't read other variables through __ENV.
- rflocust-k6 refuses a script name with characters other than letters,
  digits, dot, dash and underscore. The title no longer has double spaces.
- rflocust-k6 refuses scenario names, exec names and threshold tags that are
  not plain words, and falls back to the default HOST when the script's host
  is not a plain `host[:port]`. Hand-port reasons are written as a string
  literal. A hostile k6 script could otherwise put Robot or Python code into
  the generated files. Docs now say that `k6 inspect` runs the script's init
  code, so convert only scripts you trust.
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