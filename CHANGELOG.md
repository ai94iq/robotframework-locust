# Changelog

## Unreleased

- Changed: a Studio Build tab run is now a Robot suite run. Studio writes the tasks to a suite with two stop rules, the failure breaker and Export Report, so the run gets the same checks, Stop, Robot log and Locust report as an opened suite. New Save as suite button.
- Removed: the in-process Build tab runner and RunConfig.stop_event, which only that runner used.
- Docs: k6 converter internals and research sources moved from the user guides to CONTRIBUTING.md; docs/library.md lists keywords and links keywords.html for their arguments; docs/references.md keeps the sources a user acts on.

## 2.0.0 (2026-11-22)

- Breaking: a run stopped by the failure breaker (stop_on_fail_ratio) now fails Run Load Test, like a stop rule. Set breaker_fails=False for the old pass.
- Breaking: rflocust-k6 runs k6 inspect (needed only for computed options) only with --trust-script, because inspect runs the script's init code.
- Breaking: rflocust-k6 keeps an existing <stem>_tasks.py; pass --force to rewrite it. The report lists kept files and functions they miss.
- Breaking: an empty proxy= now reads HTTPS_PROXY / HTTP_PROXY from the environment; proxy=none turns that off. New no_proxy= bypass list.
- Breaking: the max_users check counts the users that really run; a fixed_count sum above users only warns.
- Breaking: a cpu or mem stop rule fails the run as "Inconclusive: the load machine ..." instead of as a target failure.
- Breaking: k6-generated suites refuse to start while hand-port stubs remain, unless ${ALLOW_STUBS} is True.
- New: X-Api-Key, Api-Key, X-Auth-Token and X-Access-Token are masked by default; library argument mask= adds names; masked query values and failure text are masked.
- New: verify_tls takes a CA bundle path.
- New: Should keywords warn after a run that overloaded the load machine CPU.
- New: rflocust-k6 reads literal k6 options without running the script; --trust-script is needed only for computed options. --force keeps numbered backups of the tasks file.
- New: Studio Open suite reads the suite without importing its Python libraries or variable files.
- New: stop rule metric idle (`idle > 30s`, unit required) stops a run when no response completed for that long.
- New: Run Load Test fail_on_busy_cpu=True fails the run when the load generator CPU went over 90%.
- New: library argument shared_limit (default 10000, 0 = no limit) caps values per shared name; a Take Shared Value timeout counts as a failed SHARED request.
- New: Start Locust Web and Run Distributed take host and allowed_hosts, checked like Create Load Test; Run Distributed takes users, refuses more than max_users and starts them with --autostart.
- New: Studio Stop ends a Build tab run, through a stop event on the run config.
- New: rflocust-k6 --host; the detected host is now the most common origin, with a host report row.
- New: k6-generated suites are safe by default: allowed_hosts set to the detected host, stop rules fail > 10% for 30s and idle > 30s, stop_on_fail_ratio=20%, and a safety report row.
- New: k6 check() status assertions on the response set the expected status; other checks get unsupported rows.
- Fix: k6 hand-port stubs count as failed requests and stop that user, so Should checks see them.
- Fix: k6 reports a constant-vus and shared-iterations mix as approximate with the dropped iteration caps; --host on a rerun updates the kept env file; a scaled-down stage above 0 keeps at least 1 user.
- Fix: k6 reports extra sleeps as approximate, shows helper calls with their arguments, and reads every JS number spelling without crashing.

- Fix: the generated k6 suite test is named "... - Mapped Thresholds Met", so it no longer claims unsupported thresholds were checked.
- Docs: k6-converter.md sample report, suite and stub come from a real run on samples/k6/combined.js.
- Fix: stop rule p999 now reads the 99.9th percentile, as the Should keywords do (was 9.99th).
- Fix: rflocust-k6 keeps the HTTP calls of a function that calls a local helper; only the helper gets a hand port row.
- Fix: rflocust-k6 writes a strict k6 `<` response time threshold as a maximum one ms lower; a strict error rate gets an approximate row.
- Fix: rflocust-k6 reports constant-vus and shared-iterations as mapped executors.

- Docs: user guides now match the code on safety limits, masking, Studio Stop, k6 reruns and thresholds.
- Fix: rflocust-k6 no longer stops on a k6 threshold it cannot read; the report lists it as unsupported.

## 1.0.3 (2026-11-20)

- Docs: README images use raw file URLs, so the PyPI page shows them.

## 1.0.2 (2026-11-20)

- Docs: the README uses absolute links, so the PyPI page shows its images.

## 1.0.1 (2026-11-20)

- Fix: on Python 3.11 under Linux, Studio could hang while it started a
  run. It now starts the run with posix_spawn.
- CI installs with pip and stops a stuck test after 60 seconds with a
  stack dump. 1.0.0 was tagged but never reached PyPI.

## 1.0.0 (2026-11-20)

The first release.

- Locust Studio on Linux now sees a run end. Importing Locust swaps in
  gevent's waitpid, which reports a finished child only after gevent's own
  loop has reaped it. Studio runs Qt's loop instead, so the run stayed
  "Running" forever and the Report tab stayed empty. Studio now starts Robot
  with the standard waitpid.
- The Aggregated row of the Studio stats table keeps its colours when you
  switch theme. After a switch from Graphite to Paper it kept the dark row
  colour, and its text could not be read.
- The README is shorter and points to new pages in `docs/`: `library.md`,
  `safety.md`, `studio.md` and `cli.md`, with Studio screenshots from a
  real run. `docs/index.html` is a project page for GitHub Pages, and
  `docs/keywords.html` is the keyword reference that libdoc builds.
- `CONTRIBUTING.md` lists the setup, the checks and the rules a change must
  keep.
- `.skills/using-locust-library` tells a coding agent how to write, run and
  check a load suite, with the safety limits first.
- The Locust Studio sidebar lists a suite's stop rules under the host and shows
  pacing on each user class. Class details sit on a second line, so the narrow
  sidebar no longer cuts them off.
- New keywords Put Shared Value and Take Shared Value let one step hand data it
  created to another step during a run, first in first out per name, like the
  rfswarm TestDataTable. Take waits up to a timeout and then fails the task.
- Coverage now traces gevent greenlets, so lines that run after a greenlet
  switch are counted.
- New keywords Get User Index and Get User Iteration give a task keyword the
  number of the virtual user running it and its task run count, so each user
  can build unique data. Python tasks read `user.index` and `user.iteration`.
  Users share one Robot process, so these are keywords that read the running
  user, not variables another user could overwrite. The idea comes from the
  rfswarm RFS_INDEX, RFS_ROBOT and RFS_ITERATION variables.
- New keyword Set Pacing starts a task run every interval per user, whatever
  the response time, so a slow server does not lower the planned rate. It uses
  Locust constant_pacing, like the Apply Pacing setting in rfswarm.
- New keyword Add Stop Rule stops a run once a value stays past its limit for
  a whole window, such as `p95 > 1s for 10s`, `fail > 50% for 5s` or
  `rc5?? > 20% for 5s`. `cpu` and `mem` rules watch the load machine. A rule
  fails Run Load Test unless it ends with `, stop as passed`. The syntax follows
  Taurus pass/fail criteria.
- The Locust Studio sidebar shows the real host of a suite whose host comes
  from a resource file, such as `${HOST}`. Studio reads the suite with a
  Robot dry run, which passes keyword arguments as written; the plan now
  resolves them from the variables in scope and keeps the text as written
  when a variable is unknown.
- Locust Studio runs a suite on Linux. Run crashed there with a TypeError:
  importing Locust lets gevent blank the fork call of the standard
  subprocess module, and a child started with a working folder or a
  preexec function hung. Studio now starts Robot from its own copy of the
  module, moves the child into the suite folder itself, and lowers its
  priority once it has started.
- The live feed no longer stops in the first second of a run. Locust keeps
  no minimum response time before the first request, and reading it raised
  a TypeError, so the charts stayed empty until the end.
- Locust Studio has a new look: Graphite (dark, default) and Paper (light)
  replace Dark Console, Clean Light, Neon Dark and High Contrast. One header
  row holds the tabs, the run status and the Run and Stop buttons. Numbers in
  the stats table are right-aligned in JetBrains Mono, and a failure count is
  red only above zero. The charts take the theme's colours. Inter and
  JetBrains Mono ship with Studio (SIL Open Font License 1.1).
- Locust Studio fills the Run tab stats table every second during a run, not
  only when the run ends. The run feed carries the table with each point.
- The library code is split by job: `builder.py` (build keywords),
  `checks.py` (stats and assert keywords), `parsing.py` (argument parsing) and
  `users.py` (Locust user classes). Keyword names and behavior are unchanged.
- The k6 emitter is split by job: `emit.py` (convert and host), `profile.py`
  (scenarios and thresholds to keyword lines) and `robot_files.py` (suite,
  resources and tasks text). Converter output is unchanged.
- `rflocust-k6 --env-name` accepts only letters, digits, `_`, `.` and `-`.
  The name becomes a file name and a Robot Settings line, so a newline could
  add a line to the environment file.
- Create Load Test takes `allowed_hosts`, or reads
  `LOCUSTLIBRARY_ALLOWED_HOSTS`, and refuses a host that is not on the list.
  With no list, it logs a warning and goes on.
- Run Load Test takes `stop_on_fail_ratio` and `fail_ratio_warmup`. It stops
  the run early when the failure ratio goes over the limit after the warm-up,
  and logs the reason.
- Add Get Request and Add Post Request take `expected_text`. A response
  whose body lacks it counts as failed, so a 200 error page no longer passes.
- Run Load Test logs a warning when Locust saw the generator CPU above 90%.
- Locust Studio opens a real `.robot` suite and lists its user classes and
  tasks in place of the sample lists. It runs the suite under Robot and draws
  Locust's report charts live, one point a second. The Report tab shows the
  Locust statistics table and opens the Robot log and the Locust report.
  Studio no longer crashes when it starts Robot on Python 3.15: it now uses
  the standard `subprocess` in place of gevent's.
- Run Load Test writes a JSON-lines feed of the chart values and the final
  stats when `LOCUSTLIBRARY_FEED` names a file.
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