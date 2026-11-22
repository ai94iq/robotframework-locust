# Commands

Robot Framework runs the suites. The package adds two commands: `locust-studio`
and `rflocust-k6`.

| Command | From | What it does |
|---|---|---|
| `robot <suite>` | Robot Framework | Runs a load suite. |
| `locust-studio` | the `studio` extra | Opens Locust Studio. See [studio.md](studio.md). |
| `rflocust-k6 <script>` | the `k6` extra | Converts a k6 script into a Robot project. See [k6-converter.md](k6-converter.md). |

## rflocust-k6

```
rflocust-k6 [-h] [--out OUT] [-e KEY=VALUE] [--max-users MAX_USERS]
            [--env-name ENV_NAME] [--host HOST] [--trust-script] [--force]
            script
```

Below, `<stem>` is the script file name without `.js`. For example, the stem of `combined.js` is `combined`.

| Option | Default | What it does |
|---|---|---|
| `-h`, `--help` | | Shows the help and exits. |
| `script` | | The k6 entry script. |
| `--out` | `robot` | The project folder to write. |
| `-e KEY=VALUE` | | Passed to `k6 inspect`, as `k6 -e` does. Repeat it for more values. This is not `--env-name`. |
| `--max-users` | 100 | The user ceiling the suite passes to Run Load Test. |
| `--env-name` | `dev` | Writes `resources/<env>_variables.resource`. If the file exists, it is kept, except that `--host` rewrites its `${HOST}` and `${ALLOWED_HOSTS}` lines. If the kept file has neither line, the report adds a `host \| not applied` row. Letters, digits, `_`, `.` and `-` only. |
| `--host` | most common origin | The `HOST` to write, as `http(s)://host[:port]`. Without it, the converter picks the origin the script calls most. On a tie, it picks the first one seen. The report shows `host` as detected or set by `--host`. |
| `--trust-script` | off | Must be given for every conversion. It lets the converter run `k6 inspect`. Without it, the command exits 1 with a one-line reason. |
| `--force` | off | Rewrites `resources/python/<stem>_tasks.py` when it exists. Without it, the file is kept and the report adds a `tasks file \| kept` row. Warning: the tasks file holds your hand-written task ports. `--force` overwrites it with no backup and no prompt, so copy the file first. |

The k6 binary must be on PATH. `k6 inspect` runs the script's init code as
you, so the converter refuses to run without `--trust-script`. Pass it only
for scripts you trust. The converter never runs `k6 run`.

## Keyword reference

Build the keyword reference page with libdoc:

```
python -m robot.libdoc LocustLibrary docs/keywords.html
```
