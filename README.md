# robotframework-locust

[Website](https://ai94iq.github.io/robotframework-locust/) | [PyPI](https://pypi.org/project/robotframework-locust/) |
[Keyword reference](https://ai94iq.github.io/robotframework-locust/keywords.html)

A Robot Framework library that builds and runs Locust load tests. You write
the load as a Robot suite: the library creates the Locust users, runs them
headless and checks the stats with keywords. Locust Studio shows a run live,
and `rflocust-k6` turns a k6 script into a Robot project.

Site and keyword reference: `docs/index.html` and `docs/keywords.html`,
served as the repo's GitHub page.

![Locust Studio after a 20-user run](https://raw.githubusercontent.com/ai94iq/robotframework-locust/main/docs/screenshots/studio-run.png)

## Contents

- [Install](#install)
- [Write a load suite](#write-a-load-suite)
- [Watch it in Locust Studio](#watch-it-in-locust-studio)
- [Convert a k6 script](#convert-a-k6-script)
- [Safety limits](#safety-limits)
- [Documentation](#documentation)
- [For coding agents](#for-coding-agents)
- [Contributing](#contributing)
- [License](#license)

## Install

Requires Python 3.11 or newer. Robot Framework 7.5 or newer and Locust (2.30
or newer, below 3) install with the library.

```
pip install robotframework-locust
pip install "robotframework-locust[studio]"   # adds locust-studio
pip install "robotframework-locust[k6]"       # adds rflocust-k6
```

From a checkout: `uv sync`, or `pip install .`.

## Write a load suite

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

```
robot home_load.robot
```

The suite builds the users, runs them, then checks the numbers. Run Load Test
logs a stats table and sample calls, with secrets masked. Export Report writes
the Locust HTML report beside `log.html`.

The library has 28 keywords: user classes, pacing, stop rules, Python tasks,
per-user numbers, data handed between users, and checks for response time,
error rate and throughput. See [docs/library.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/library.md).

## Watch it in Locust Studio

```
locust-studio
```

Open a suite (Ctrl+O) and press Run (Ctrl+R). Studio runs the suite under
Robot and updates the stats table and Locust's three charts every second.
When the run ends, the Report tab opens the Robot log and the Locust report.
Studio has a dark and a light theme and runs on Windows and Linux. See
[docs/studio.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/studio.md).

![The Studio Run tab in the dark theme, during a run](https://raw.githubusercontent.com/ai94iq/robotframework-locust/main/docs/screenshots/studio-run-graphite.png)

## Convert a k6 script

```
rflocust-k6 checkout.js --out robot
robot -v ENV:dev robot/tests
```

The converter reads the script's options with `k6 inspect` and scans its
functions for plain HTTP calls. Stages, thresholds and simple requests become
keywords. A function it cannot read becomes a Python task that raises
`NotImplementedError` until you port it, and a report lists each item as
mapped, approximate or hand port. The k6 binary must be on PATH.
`k6 inspect` runs the script's init code as you, so convert only scripts you
trust. See [docs/k6-converter.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/k6-converter.md).

## Safety limits

A load test can take a server down. These limits are built in:

- Run Load Test refuses a run above `max_users` (default 100).
- Create Load Test refuses a host that is not on `allowed_hosts`.
- `Add Stop Rule    p95 > 1s for 10s` and `stop_on_fail_ratio` stop a run
  early.
- `expected_text` fails a 200 that carries an error page.
- The Locust web UI and distributed mode bind 127.0.0.1 only.

Read [docs/safety.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/safety.md) before you point a run at a host you do
not own.

## Documentation

| Page | What it covers |
|---|---|
| [docs/library.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/library.md) | Writing suites, every keyword, Python tasks, reports |
| [docs/safety.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/safety.md) | Every limit and how to set it |
| [docs/studio.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/studio.md) | Locust Studio |
| [docs/k6-converter.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/k6-converter.md) | The k6 mapping, its limits, porting by hand |
| [docs/cli.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/cli.md) | The commands and their options |
| [docs/keywords.html](https://ai94iq.github.io/robotframework-locust/keywords.html) | Keyword reference, built by libdoc |
| [docs/references.md](https://github.com/ai94iq/robotframework-locust/blob/main/docs/references.md) | Locust and Robot Framework sources |
| [CHANGELOG.md](https://github.com/ai94iq/robotframework-locust/blob/main/CHANGELOG.md) | Changes per release |

## For coding agents

`.skills/using-locust-library/SKILL.md` tells a coding agent how to write,
run and check a load suite with this library, with the safety limits first.
Copy the folder into your agent's skills folder to use it in another repo.

## Contributing

See [CONTRIBUTING.md](https://github.com/ai94iq/robotframework-locust/blob/main/CONTRIBUTING.md) for the setup, the checks and the rules
a change must keep.

## License

MIT. See [LICENSE](https://github.com/ai94iq/robotframework-locust/blob/main/LICENSE).
