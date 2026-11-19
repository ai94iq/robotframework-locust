# Python Library Best Practices 2026 (robotframework-locust)

## pyproject.toml structure (build-system, project metadata, optional deps, tool config)

### Takeaway
A single `pyproject.toml` with a `[build-system]` table is the 2026 standard; use PEP 639 SPDX licenses, `[dependency-groups]` for dev tools (never extras), and per-tool `[tool.*]` tables. uv/hatchling are the recommended backends.

### Cited Findings
- `[build-system]` table should always be present regardless of backend; example values: Hatchling `requires = ["hatchling >= 1.26"]`, setuptools `>= 77.0.3`, Flit `flit_core >= 3.12.0, <5`, uv-build `>= 0.13, <0.14`. — [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- Four TOML tables: `[build-system]`, `[project]`, `[dependency-groups]`, `[tool]`. — [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- PEP 639 (2026): `license = "MIT"` SPDX expression + `license-files = ["LICENSE"]`; old dict form deprecated. — [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- Dev tools belong in `[dependency-groups]` (PEP 735), never in extras, so they are not published in wheels. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)
- `requires-python = ">=3.11"` (or `>=3.13` for new projects) gates install; classifiers only affect PyPI browsing. — [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- `project.optional-dependencies` (extras) are for optional runtime features; convenience `all` extra can reference other extras: `all = ["pkg[gui, cli]"]`. — [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)

### Inferences
- For robotframework-locust (Python >=3.11), set `requires-python = ">=3.11"` and `target-version = "py311"` in Ruff to avoid proposing 3.12+ syntax.

### Gaps
- None identified.

## src layout, versioning, and packaging for PyPI (trusted publishing, wheels)

### Takeaway
Use src layout, single-source version via dynamic field read from `__version__` (or Git tag), build sdist+wheel with `python -m build`, and publish with trusted publishing (OIDC, no API tokens) via `pypa/gh-action-pypi-publish`.

### Cited Findings
- src layout is the popular recommended layout (package under `src/`). — [Real Python pyproject guide](https://realpython.com/python-pyproject-toml/)
- Single-sourcing version: mark `dynamic = ["version"]` and let backend read `__version__` or Git tag; see Single-sourcing the Project Version discussion. — [Writing your pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/)
- Build with `python -m build` (produces sdist + wheel); deprecated `python setup.py ...` commands. — [Modernize setup.py guide](https://packaging.python.org/en/latest/guides/modernize-setup-py-project/)
- Trusted publishing uses OIDC: configure pending publisher on PyPI, set `permissions: id-token: write`, use `pypa/gh-action-pypi-publish@release/v1`; no API tokens needed. — [Publishing via GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- Build job must be separate from publish jobs; publish jobs only download artifacts. — [Publishing via GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- `pypa/gh-action-pypi-publish` v1.11.0+ generates PEP 740 attestations by default. — [Publishing via GitHub Actions](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/)
- Wheels preferred over sdists; pin Python minor in CI to avoid source builds. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)

### Inferences
- For a pure-Python Robot library, a universal wheel (`py3-none-any`) is sufficient; no cibuildwheel needed.

### Gaps
- Exact hatchling version-source config (`[tool.hatch.version]` path) not verified from primary source here; consult hatch docs.

## Testing (pytest fixtures, parametrization, coverage, tox/nox matrix)

### Takeaway
Use pytest with fixtures/parametrize, enforce coverage thresholds (commonly 80%), and run a Python-version matrix via tox or nox (or uv). Run `uv sync --locked` in CI to verify lock currency.

### Cited Findings
- pytest 9.x (tested 9.2.0) with `testpaths = ["tests"]` in `[tool.pytest.ini_options]`. — [Python tooling stack 2026](https://pythonresources.com/guides/python-tooling-stack-2026/)
- Coverage minimum 80% in strict quality configs. — [ctoc strict config](https://github.com/robotijn/ctoc/blob/main/skills/quality-configs/python/strict.md)
- uv commands: `uv sync`, `uv sync --locked` (fail if stale), `uv run pytest`. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)

### Inferences
- Parametrize with `@pytest.mark.parametrize` and share setup via fixtures in `conftest.py`; standard pytest patterns apply.

### Gaps
- Nox/tox-specific matrix config not found in sources; standard nox sessions pattern applies (unverified detail).

## Linting/type checking (ruff, mypy)

### Takeaway
Use Ruff (lint + format) with `extend-select` (never replace defaults) plus mypy in strict mode. Skip Ruff's `ANN` rules since mypy strict already enforces annotations.

### Cited Findings
- Ruff: use `extend-select` to add rules without dropping defaults; `select` replaces defaults. — [Ruff settings](https://docs.astral.sh/ruff/settings/), [code quality stack 2026](https://blog.marcosalonso.dev/the-complete-python-code-quality-stack-in-2026-ruff-mypy)
- Ruff strict config selects many families (E,W,F,I,B,C4,UP,ARG,SIM,TCH,PTH,ERA,PL,RUF,S,A,COM,DTZ,T10,EXE,ISC,ICN,G,INP,PIE,PYI,Q,RSE,RET,SLF,SLOT,TID,INT,PERF,FURB,LOG) with per-file ignores for tests. — [ctoc strict config](https://github.com/robotijn/ctoc/blob/main/skills/quality-configs/python/strict.md)
- mypy `strict = true` enables all strict flags; add `namespace_packages`, `show_error_codes`, `enable_error_code = ["ignore-without-code", "redundant-expr", "truthy-bool"]`. — [code quality stack 2026](https://blog.marcosalonso.dev/the-complete-python-code-quality-stack-in-2026-ruff-mypy)
- mypy strict is the baseline used by FastAPI/SQLAlchemy/Pydantic. — [Modern Python tooling 2026](https://softaims.com/blog/modern-python-tooling-uv-ruff-mypy-2026)
- Do not use Ruff `ANN`; mypy strict handles annotations. — [code quality stack 2026](https://blog.marcosalonso.dev/the-complete-python-code-quality-stack-in-2026-ruff-mypy)
- Ruff infers `target-version` from `requires-python`. — [Ruff settings](https://docs.astral.sh/ruff/settings/)

### Inferences
- For heavy third-party deps without stubs (locust, robotframework), add `[[tool.mypy.overrides]]` with `ignore_missing_imports = true` for those modules.

### Gaps
- None.

## Security (bandit, pip-audit, detect-secrets in CI)

### Takeaway
Run three distinct scanners in CI: pip-audit (deps/CVEs), bandit (code patterns), detect-secrets (credentials), plus Dependabot for auto-PRs. Use thresholds and baselines to avoid noise.

### Cited Findings
- pip-audit (PyPA) checks installed packages/requirements against Python advisory DB + OSV; resolves transitive deps. — [Python security tools 2026](https://safeguard.sh/resources/blog/python-security-tools)
- Bandit SAST for insecure patterns (assert for security, subprocess shell=True, hardcoded passwords, weak hashes, unsafe YAML load, eval); tune with `# nosec Bxxx` inline and `-ll -ii` thresholds. — [Python security tools 2026](https://safeguard.sh/resources/blog/python-security-tools)
- detect-secrets maintains a baseline (`.secrets.baseline`) for adoption on existing repos; run as pre-commit hook. — [Python security tools 2026](https://safeguard.sh/resources/blog/python-security-tools)
- CI example runs all three via uv tool install; bandit `-ll` gates medium+; pip-audit fails on CVEs; detect-secrets checks baseline. — [CI security guide](https://github.com/wdm0006/python-skills/blob/main/skills/python/security-audit/CI_SECURITY.md)
- Dependabot (pip + github-actions ecosystems, weekly, grouped dev deps) closes the loop with pip-audit. — [CI security guide](https://github.com/wdm0006/python-skills/blob/main/skills/python/security-audit/CI_SECURITY.md)
- Block on fixable CVEs by default; unfixable reported but non-blocking. — [developmentseed action](https://github.com/developmentseed/action-python-security-auditing)

### Inferences
- For a library wrapping Locust, run bandit on `src/` only; tests may use `assert` (ignore B101 in tests).

### Gaps
- None.

## Dependency management (pinning, extras, lazy imports for heavy deps)

### Takeaway
Declare ranges with major-version bounds in pyproject.toml, commit a lockfile (uv.lock) with hashes, keep heavy deps (locust) as extras or lazy-imported, and use `[dependency-groups]` for dev.

### Cited Findings
- Declared deps use ranges (`>=5.2,<6.0`); lockfile pins exact versions with hashes; commit lockfile. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)
- Upper bounds on major version only; capping minors blocks security patches. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)
- Dependency groups (PEP 735) never ship in wheels; extras are for optional runtime features. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)
- Keep dependency list thin; every dep inherited by consumers. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)
- `uv lock --locked` verifies committed lock matches manifest; `uv sync --frozen` for Docker. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)
- Lazy imports for heavy deps: avoid side effects on import; a shared package that touches settings on import cannot be used in tests. — [DjangoZen packaging guide](https://www.djangozen.com/tutorials/packaging-python-for-production-uv-pyproject-wheels-lockfiles-and-private-indexes/)

### Inferences
- For robotframework-locust, make `locust` a core dependency but import lazily inside keywords to keep `--dryrun`/import fast; expose `locust` extra only if optional.

### Gaps
- No measured lazy-import pattern verified; standard `import` inside function body applies.