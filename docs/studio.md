# Locust Studio

A desktop window that opens a load suite, runs it under Robot and shows the
run live. It ships as the `studio` extra:

```
pip install "robotframework-locust[studio]"
locust-studio
```

Studio needs PySide6 and pyqtgraph, which the extra installs. It runs on
Windows and Linux.

![Locust Studio after a 20-user run in the Paper theme](screenshots/studio-run.png)

## Contents

- [Open a suite](#open-a-suite)
- [Run it](#run-it)
- [The report](#the-report)
- [Build tab](#build-tab)
- [Settings](#settings)
- [Keys](#keys)

## Open a suite

**Open suite...** (Ctrl+O) reads a `.robot` load suite with a Robot dry
run, so nothing is sent. The sidebar shows the suite's host and stop rules,
then each user class with its weight, wait time or pacing. Pick a class to see
its tasks. A host that comes from a variable, such as `${HOST}`, shows its
value when the variable is in scope.

## Run it

**Run** (Ctrl+R) starts Robot on the suite at low priority, into a temporary
output folder. Robot's console output goes to the live log on the right.
Every second the stats table and three charts update: requests and failures
per second, the 50th and 95th percentile response times, and users.

![The Run tab in the Graphite theme, 18 seconds into a run](screenshots/studio-run-graphite.png)

**Stop** ends the Robot process.

Run Load Test writes the live feed only when the `LOCUSTLIBRARY_FEED`
environment variable names a file. Studio sets it for its own runs, so a
suite needs no change to show in Studio.

## The report

When the run ends, the Report tab shows the request count, the failures and
Locust's statistics table. **Open Robot log** opens `log.html`. **Open
Locust report** opens the HTML report that Export Report wrote.

![The Report tab in the Paper theme](screenshots/studio-report.png)

## Build tab

With no suite open, Run runs the HTTP tasks put together on the Build tab,
with the users, spawn rate and run time set on the Run tab.

## Settings

Studio has two themes: Graphite (dark, the default) and Paper (light).
[DESIGN.md](../DESIGN.md) describes both. Settings also has a right-to-left
layout switch. Studio ships the Inter and JetBrains Mono fonts under the SIL
Open Font License 1.1 (`studio/fonts/`); without them it falls back to
Segoe UI and Consolas.

## Keys

| Key | Action |
|---|---|
| Ctrl+O | Open a suite |
| Ctrl+R | Run |
| Ctrl+, | Settings |
