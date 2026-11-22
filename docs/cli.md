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
| `-e KEY=VALUE` | | Passed to `k6 inspect`, as `k6 -e` does. It is used only when `k6 inspect` runs. Repeat it for more values. This is not `--env-name`. |
| `--max-users` | 100 | The user ceiling the suite passes to Run Load Test. |
| `--env-name` | `dev` | Writes `resources/<env>_variables.resource`. If the file exists, it is kept, except that `--host` rewrites its `${HOST}` and `${ALLOWED_HOSTS}` lines. If the kept file has neither line, the report adds a `host \| not applied` row. If the kept file has no `${ALLOW_STUBS}` line, the converter adds it as `${False}` and the report adds an `env file \| updated` row. Letters, digits, `_`, `.` and `-` only. |
| `--host` | most common origin | The `HOST` to write, as `http(s)://host[:port]`. Without it, the converter picks the origin the script calls most. On a tie, it picks the first one seen. The report shows `host` as detected or set by `--host`. |
| `--trust-script` | off | Lets the converter run `k6 inspect`. It is needed only when `export const options` is not a plain literal. Without it, such a script makes the command exit 1. The message names the option that is not a literal. |
| `--force` | off | Rewrites `resources/python/<stem>_tasks.py` when it exists. Without it, the file is kept and the report adds a `tasks file \| kept` row. Warning: the tasks file holds your hand-written task ports. With `--force`, the old file is first copied to `resources/python/<stem>_tasks.py.bak` (`.bak.1`, `.bak.2` and so on when taken; no backup is overwritten), and the report adds a `tasks file \| backed up` row that names the backup. When the old file equals the new text, no backup is made. There is no prompt. |

The converter reads `export const options` from the script itself when every
value is a literal. The report then shows `options | read statically`. It does
not run k6 for this.

When an option is computed, the converter falls back to `k6 inspect`. The
report then shows `options | from k6 inspect`. `k6 inspect` runs the script's
init code as you, so this path needs `--trust-script` and the k6 binary on
PATH. Pass `--trust-script` only for scripts you trust. The converter never
runs `k6 run`.

The generated suite will not start while hand-port stubs remain in the tasks
file. To run it anyway, set `${ALLOW_STUBS}` to `${True}` in the env file. The
converter writes it as `${False}`.

## Keyword reference

Build the keyword reference page with libdoc:

```
python -m robot.libdoc LocustLibrary docs/keywords.html
```
