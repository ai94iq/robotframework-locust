# GitHub Robot Framework / Locust / Load Testing Prior Art

## Key Question: Existing robotframework-locust or similar libraries

### Takeaway
No dedicated `robotframework-locust` library exists on PyPI/GitHub as of the research date. The established pattern is to use Locust as the outer driver invoking Robot Framework runs per user (often via `subprocess.Popen`), or to use RF-native swarms (rfswarm) / Oxygen handlers wrapping Locust. A direct in-process integration is sparse because `robot.run` carries global state that breaks concurrent users.

### Cited Findings
- Stack Overflow "Parallel robot framework tests via locust" (2021, updated Mar 2025) documents the canonical integration: `robot.run('robot_test1.robot')` inside a Locust `HttpUser` task. Shared global state of `robot.run` causes Chrome instances to collide; the working fix reported Mar 2025 is `subprocess.Popen(['robot', '--suite', suite, '.'])` per user for process isolation. - [Source](https://stackoverflow.com/questions/65810120/parallel-robot-framework-tests-via-locust)
- `robotframework-oxygen` (eficode) provides a `BaseHandler` framework where a `LocustHandler` wraps Locust execution: `run_locust(result_file, command, ...)` runs the locust command line and parses CSV output into RF-friendly results. Closest "RF library invoking Locust" prior art. - [Source](https://github.com/eficode/robotframework-oxygen/blob/master/DEVGUIDE.md)
- `rfswarm` (damies13) is the most mature RF-native load tool: 128 stars, 27 forks, GPL-3.0, 9,084 commits, manager/agent/reporter components, Python 3.7+, PyPI `rfswarm-manager` 1.6.0 (2026-08-05). Runs real RF test cases across multiple agents with ramp-up and per-robot variable injection (Index, Robot number, Iteration). - [Source](https://github.com/damies13/rfswarm) ; [PyPI](https://pypi.org/project/rfswarm-manager)
- rfswarm provides `TestDataTable` (separate tool by same author) for unique per-robot data (e.g. userids), equivalent to LoadRunner VTS. - [Source](https://forum.robotframework.org/t/can-rfswarm-read-in-variables-and-pass-them-to-the-robot-framework-test-case-being-run/4925)
- rfswarm was presented at RoboCon 2024 ("Performance test in a day using Robot Framework and RFSwarm") and used at RoboCon 2025 for PostgreSQL migration load testing. - [Source](https://pretalx.com/robocon-2024/talk/LHTGWU) ; [Source](https://www.robotmk.org/en/blog/robocon25-recap)

### Inferences
- For a new `robotframework-locust` library, process isolation per virtual user (subprocess) is the safe default; in-process `robot.run` is not viable under concurrency.
- rfswarm's agent/manager/reporter split and `TestDataTable` are reusable design references for data feeding and distributed execution.

### Gaps
- No quantitative benchmark comparing rfswarm vs Locust-driven RF; no maintained `robotframework-locust` PyPI package found.

## Key Question: How other RF performance/load libraries structure things

### Takeaway
rfswarm uses a three-component architecture (manager GUI, agents, reporter) communicating via JSON REST; Oxygen uses a `BaseHandler` plugin pattern with YAML config and a listener; both wrap external tools rather than reimplementing load generation.

### Cited Findings
- rfswarm: manager plans/runs scenarios, agents run RF tests, reporter aggregates CSV; agent selection by least-utilized resource; warns at 80% / critical at 95% utilization. - [Source](https://github.com/damies13/rfswarm)
- Oxygen: handler-based, `run_command_line` + `validate_path`, `--listener oxygen.listener`, config via `config.yml`; Locust handler example runs `locust -f ... --headless --csv=...`. - [Source](https://github.com/eficode/robotframework-oxygen/blob/master/DEVGUIDE.md)
- `pabot` (mkorpela) is the standard parallel RF executor (referenced as fallback when Locust integration fails). - [Source](https://github.com/mkorpela/pabot)
- UiPath Test Manager supports performance scenarios with virtual users running RF/automation tests, with dry-run then full execution phases. - [Source](https://docs.uipath.com/test-manager/automation-cloud/latest/user-guide/executing-performance-scenarios)

### Gaps
- rfswarm is GPL-3.0; license compatibility must be checked if reusing code in an Apache-2.0 RF library.

## Key Question: GitHub repos for RF libraries using robotlibcore HybridCore with component classes

### Takeaway
`robotframework/PythonLibCore` (69 stars, 29 forks, Apache-2.0, v4.6.0 on PyPI 2026-05-14) is the canonical implementation: library inherits `HybridCore`/`DynamicCore`, passes a list of component class instances to `library_components`, keywords decorated with `@keyword`. Used by SeleniumLibrary and Browser library.

### Cited Findings
- PythonLibCore README: "Library must inherit either HybridCore or DynamicCore"; "Provide a list of class instances implementing keywords to library_components"; keywords decorated with `@keyword`; main class may also hold keywords. - [Source](https://github.com/robotframework/PythonLibCore)
- PyPI `robotframework-pythonlibcore` 4.6.0, released 2026-05-14, supports two latest RF versions, ~298k weekly downloads. - [Source](https://pypi.org/project/robotframework-pythonlibcore/)
- SeleniumLibrary and Browser library are the reference consumers. - [Source](https://github.com/robotframework/PythonLibCore)

### Inferences
- A new `robotframework-locust` library should follow this component-class pattern (e.g. `LocustRunner`, `ResultParser`, `StatsReporter`) for consistency with the RF ecosystem.

### Gaps
- Did not locate other third-party RF libraries beyond SeleniumLibrary/Browser that demonstrate HybridCore component decomposition; search returned only PythonLibCore docs and generic repos.

## Key Question: RF libraries with PySide/Qt GUI components

### Takeaway
`robotframework-qtexpert` (PyPI 0.1.2, released 2026-01-21, Apache-2.0) is the active RF Qt library, supporting PySide2/6 and PyQt5/6 in agent mode plus accessibility mode, cross-platform. `ROBOT-RUNNER` (PyQt6) is a GUI test runner, not a library.

### Cited Findings
- `robotframework-qtexpert`: unified RF library for Qt apps; dual-mode (agent in-process vs accessibility); supports PyQt5/6, PySide2/6; Python >=3.8. - [Source](https://pypi.org/project/robotframework-qtexpert/)
- `ROBOT-RUNNER-COMMUNITY/ROBOT-RUNNER`: GUI to run/manage RF tests, uses PyQt6 and pabot; 3 stars. - [Source](https://github.com/ROBOT-RUNNER-COMMUNITY/ROBOT-RUNNER)
- `pyedifice` (507 stars) is a declarative Qt GUI framework using PySide6/PyQt6, not an RF library but a candidate GUI toolkit. - [Source](https://github.com/pyedifice/pyedifice)
- Other GUI-related RF libs: `robotframework-pywinautolibrary`, `robotframework-PyWindowsGuiLibrary`, `robotframework-flaui`, `robotframework-sapguilibrary`, `robotframework-imagehorizonlibrary`. - [Sources](https://github.com/AnoopGR/robotframework-pywinautolibrary) ; [PyPI](https://pypi.org/project/robotframework-PyWindowsGuiLibrary/)

### Inferences
- If the new library needs a manager GUI (like rfswarm), PySide6/PyQt6 via qtexpert or pyedifice are viable; otherwise keep CLI-only to match Oxygen's approach.

### Gaps
- No RF library combines Locust + Qt GUI; rfswarm's manager GUI is Tk/legacy (not Qt) per docs.

## Additional: general load-testing / RF-adjacent repos

### Cited Findings
- `jg8481/go-language-rpa-tests`: Go tools + RF RPA, uses vegeta for load testing (2 stars, 2024). - [Source](https://github.com/jg8481/go-language-rpa-tests)
- `Nikita-Filonov/python-load-tests`: production-grade Locust + HTTPX + CI/CD framework (4 stars, 2025). - [Source](https://github.com/Nikita-Filonov/python-load-tests)
- `locustio/locust`: 28,285 stars, supports running as a library (`Environment`, `create_local_runner`, `spawn_users`). - [Source](https://github.com/locustio/locust)

### Gaps
- Locust-as-library API (`env.runner.spawn_users`) could enable in-process RF invocation per user, but RF global-state isolation remains unverified; no source found testing this combination.