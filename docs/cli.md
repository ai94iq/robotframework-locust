# Commands

The library is used from Robot Framework. The package adds two commands.

| Command | From | What it does |
|---|---|---|
| `robot <suite>` | Robot Framework | Runs a load suite. |
| `locust-studio` | the `studio` extra | Opens Locust Studio. See [studio.md](studio.md). |
| `rflocust-k6 <script>` | the `k6` extra | Converts a k6 script into a Robot project. See [k6-converter.md](k6-converter.md). |

## rflocust-k6

```
rflocust-k6 [-h] [--out OUT] [-e ENV] [--max-users MAX_USERS]
            [--env-name ENV_NAME] script
```

| Option | Default | What it does |
|---|---|---|
| `script` | | The k6 entry script. |
| `--out` | `robot` | The project folder to write. |
| `-e KEY=VALUE` | | Passed to `k6 inspect`, as `k6 -e` does. Repeat it for more values. |
| `--max-users` | 100 | The user ceiling the suite passes to Run Load Test. |
| `--env-name` | `dev` | The environment file to create. Letters, digits, `_`, `.` and `-` only. |

The k6 binary must be on PATH. `k6 inspect` runs the script's init code as
you, so convert only scripts you trust. The converter never runs `k6 run`.

## Keyword reference

Build the keyword reference page with libdoc:

```
python -m robot.libdoc LocustLibrary docs/keywords.html
```
