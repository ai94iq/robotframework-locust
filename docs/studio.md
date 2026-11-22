# Locust Studio

A desktop window that opens a load suite, runs it under Robot and shows the
run live. It ships as the `studio` extra:

```
pip install "robotframework-locust[studio]"
locust-studio
```

Studio needs PySide6 and pyqtgraph, which the extra installs. It runs on
Windows and Linux. It is not tested on macOS.

![Locust Studio after a 20-user run in the Paper theme](screenshots/studio-run.png)

## Contents

- [Open a suite](#open-a-suite)
- [Run it](#run-it)
- [The report](#the-report)
- [Build tab](#build-tab)
- [Settings](#settings)
- [Keys](#keys)

## Open a suite

**Open suite...** (Ctrl+O) reads a `.robot` load suite and its resource
files without running them. No request is sent, and no Python library or
variable file is imported.

The sidebar shows the suite's host and stop rules, then each user class
with its weight, wait time or pacing. Pick a class to see its tasks. A host
that comes from a variable, such as `${HOST}`, shows its value when the
variable is set in a `*** Variables ***` section of the suite or one of its
resource files. Values from variable files or the command line are not read.
A variable that a user keyword gets through `[Arguments]` shows the value
passed to it. When you open a folder, each child suite is read with its own
variables and keywords.
When the variable is not found, the sidebar shows the
variable as written, such as `${HOST}`.

## Run it

**Run** (Ctrl+R) starts Robot on the suite at low priority. Robot writes its
output to a new folder in the system temp folder, named `locust-studio-`
and a random suffix. The live log shows the folder path when the run starts.
Studio does not delete the folder, so the Report buttons work while it
exists. Old `locust-studio-*` folders stay in the system temp folder (`%TEMP%`
on Windows, usually `/tmp` on Linux) until you delete them. Robot's console output goes to the live log on the right.
Every second the stats table and three charts update: requests and failures
per second, the 50th and 95th percentile response times, and users.

![The Run tab in the Graphite (dark) theme, 18 seconds into a run](screenshots/studio-run-graphite.png)

**Stop** ends the Robot process of a suite run. The live log shows
"Stopped." and the status shows "Run ended, Robot exit code N", with the
exit code Robot returned.

**Stop** also ends a Build tab run (see [Build tab](#build-tab)). The live
log shows "Stopping...", the status shows "Run stopped", and the run does
not count as a failure.

Run Load Test writes the live feed only when the `LOCUSTLIBRARY_FEED`
environment variable names a file. Studio sets it for its own runs, so a
suite needs no change to show in Studio.

## The report

When the run ends, the Report tab shows the request count, the failures and
Locust's statistics table. **Open Robot log** opens `log.html`. **Open
Locust report** opens the HTML report that Export Report wrote. If the
suite did not call Export Report, this button stays disabled. If the run
wrote no `log.html`, **Open Robot log** stays disabled.

A Build tab run shows its request count, failures and statistics table on
the Report tab too. It writes no Robot log and no Locust report, and it
does not change the two buttons.

![The Report tab in the Paper theme](screenshots/studio-report.png)

## Build tab

![The Build tab](screenshots/studio-build.png)

With no suite open, Run runs the HTTP tasks put together on the Build tab,
with the users, spawn rate and run time set on the Run tab. Studio has no
action that closes a suite. So the Build tab runs only before the first
suite is opened. To use it after that, start Studio again.

1. On the Build tab, set **Host** (default `http://127.0.0.1:8765`),
   **Wait min** and **Wait max** (defaults `0.1s` and `0.5s`).
2. For each task, enter a name, pick GET or POST, enter a path and a weight,
   then select **Add task**. A POST task sends no body. A task passes when
   the response status is 200. The Build tab has no fields for headers, a
   body or the expected status.
3. On the Run tab, set **Users**, **Spawn rate** and **Run time**
   (defaults 10, 2 and `10s`), then select **Run**.

Studio runs these tasks in its own Python process, without Robot, through the same keywords a suite
uses: Create Load Test, Set Wait Time, Add Get Request or Add Post Request,
and Run Load Test. So the same host checks apply: the host must be valid, and
when `LOCUSTLIBRARY_ALLOWED_HOSTS` is set, it must be in that list. Run Load
Test uses its default `max_users` of 100. A Build tab run has no stop rules
and no Should checks. To end it early, select **Stop**. The run then ends
as stopped from Studio, not as a failure. A Build tab run writes its live
feed to a new `locust-studio-*` folder in the system temp folder. Studio
does not delete this folder either.

## Settings

Studio has two themes: Graphite (dark, the default) and Paper (light).
Settings also has a right-to-left layout switch. [DESIGN.md](../DESIGN.md)
describes the themes and the fonts, which ship in
`src/LocustLibrary/studio/fonts/`.

## Keys

| Key | Action |
|---|---|
| Ctrl+O | Open a suite |
| Ctrl+R | Run |
| Ctrl+, | Settings |
