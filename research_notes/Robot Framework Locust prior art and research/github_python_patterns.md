# GitHub Modern Python Library Patterns (2025-2026)

## src-layout exemplars with pyproject.toml, dependency-groups, PEP 639

### Takeaway
Modern, well-maintained Python libraries use a `src/` layout with `pyproject.toml` (PEP 517/518), hatchling or setuptools as build backend, PEP 621 metadata, and PEP 639 license expressions; dev dependencies live in `[dependency-groups]` (PEP 735) rather than `[project.optional-dependencies]`.

### Cited Findings
- httpx uses hatchling build backend with `[project]` PEP 621 metadata, `license = "BSD-3-Clause"` (PEP 639-style SPDX expression), `requires-python = ">=3.10"`, and optional deps under `[project.optional-dependencies]` (brotli, cli, http2, socks, zstd). — [httpx/pyproject.toml](https://raw.githubusercontent.com/encode/httpx/master/pyproject.toml)
- httpx version is dynamic via `[tool.hatch.version] path = "httpx/__version__.py"` and readme assembled via fancy-pypi-readme hook. — [httpx/pyproject.toml](https://raw.githubusercontent.com/encode/httpx/master/pyproject.toml)
- PythonLibCore (Robot Framework library core) uses `src/` layout with `[tool.setuptools.packages.find] where = ["src"]`, setuptools build backend, `license = "Apache-2.0"` SPDX expression, and `requires-python = ">=3.10, <4"`. — [PythonLibCore/pyproject.toml](https://raw.githubusercontent.com/robotframework/PythonLibCore/main/pyproject.toml)
- PythonLibCore exposes `__version__` in `src/robotlibcore/__init__.py` and reads it dynamically via `[tool.setuptools.dynamic] version = {attr = "robotlibcore.__version__"}`. — [PythonLibCore/__init__.py](https://raw.githubusercontent.com/robotframework/PythonLibCore/main/src/robotlibcore/__init__.py)
- Dependency groups are defined under `[dependency-groups]` in pyproject.toml per PEP 735, distinct from optional dependencies. — [Python Packaging User Guide](https://packaging.python.org/en/latest/specifications/dependency-groups)
- `uv init --package` scaffolds a src layout by default. — [modern-python skill](https://github.com/gebl/anvil-skill-marketplace/blob/main/plugins-claude/modern-python/skills/modern-python/SKILL.md)

### Inferences
- PEP 639 license expressions (SPDX identifiers as plain strings) are now the norm; classifier-based License classifiers are being phased out.
- For a Robot Framework library like robotframework-locust, PythonLibCore's setuptools src-layout is the closest prior art.

### Gaps
- No single canonical 2025 example combining dependency-groups + PEP 639 + src layout + hatchling was located; httpx still uses optional-dependencies for extras.

## lazy imports for heavy deps (importlib, __getattr__)

### Takeaway
Module-level `__getattr__` (PEP 562) plus `importlib.util` is the dominant lazy-import mechanism; the scientific-Python SPEC 1 endorses `lazy_loader` or module `__getattr__`; PEP 690 (lazy imports) is still a proposal with runtime overhead concerns.

### Cited Findings
- PEP 562 allows `__getattr__` on modules, enabling on-demand import when an attribute is accessed. — [snarky.ca lazy importing](https://snarky.ca/lazy-importing-in-python-3-7/)
- Scientific Python SPEC 1 recommends lazy loading of subpackages via `lazy_loader` or module `__getattr__`. — [scientific-python.org SPEC 0001](https://scientific-python.org/specs/spec-0001)
- geoai uses PEP 562 module-level `__getattr__` so `import geoai` stays fast without requiring torch/torchvision/transformers. — [geoai/__init__.py](https://raw.githubusercontent.com/opengeos/geoai/main/geoai/__init__.py)
- `lateimport` provides a factory for the `__getattr__` hook for dispatch-table-based lazy loading. — [lateimport on PyPI](https://pypi.org/project/lateimport)
- PEP 690 proposes interpreter-level lazy imports but imposes Python-level `__getattr__`/`__getattribute__` overhead on every attribute access. — [PEP 690](https://peps.python.org/pep-0690)

### Inferences
- For robotframework-locust, lazy-importing heavy deps (locust, robot framework internals) via `__getattr__` in `__init__.py` keeps `import robotframework_locust` fast and avoids pulling optional deps at import time.

### Gaps
- No widely-cited 2025 example of lazy imports inside a Robot Framework library specifically.

## Trusted publishing workflows (GitHub Actions)

### Takeaway
Trusted publishing (OIDC) is the standard: build in one job, publish in a separate job with `permissions: id-token: write`, environment `pypi`, no long-lived tokens; `uv publish` / `pypa/gh-action-pypi-publish` consume the OIDC token.

### Cited Findings
- PyPI Trusted Publishing connects a GitHub repo + workflow to a PyPI project, eliminating stored API tokens. — [PyPI trusted publishers](https://docs.pypi.org/trusted-publishers/)
- Packaging guide recommends trusted publishing via GitHub Actions. — [Python Packaging User Guide](https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows)
- astral-sh/trusted-publishing-examples ships a complete workflow: build job (checkout, `uv build`, smoke tests, upload artifact) then publish job (`needs: build`, environment `pypi`, `permissions: id-token: write`, download artifact, `uv publish`). — [release.yml](https://raw.githubusercontent.com/astral-sh/trusted-publishing-examples/main/.github/workflows/release.yml)
- httpx migrated to trusted publishing (discussion). — [encode/httpx#3732](https://github.com/encode/httpx/discussions/3732)

### Inferences
- For robotframework-locust, adopt the astral example verbatim, swapping `uv` for the project's chosen build tool; pin action SHAs.

### Gaps
- No example located that combines trusted publishing with setuptools + src layout specifically; the astral example assumes `uv build`.

## Hybrid / Dynamic library patterns (robotlibcore)

### Takeaway
PythonLibCore provides `HybridCore` (static keyword names via `get_keyword_names` + `get_keyword_documentation` etc.) and `DynamicCore` (adds `run_keyword` dispatch); keywords are decorated with Robot Framework's `@keyword` decorator and components are passed via `library_components`.

### Cited Findings
- PythonLibCore: implement keywords in component classes decorated with `@keyword`, pass instances to `HybridCore`/`DynamicCore.__init__` via `library_components`. — [PythonLibCore README](https://github.com/robotframework/PythonLibCore/blob/main/README.md)
- `DynamicCore(HybridCore)` implements `run_keyword(name, args, kwargs)` dispatching to `self.keywords[name]`. — [robotlibcore.py (ef35336)](https://github.com/robotframework/PythonLibCore/blob/ef35336fbc895d3d329a6d61be52501c2a5a54d4/src/robotlibcore.py)
- Robot Framework's hybrid library API uses `get_keyword_names` to declare keywords; dynamic adds `run_keyword`. — [robot.api.interfaces](https://robot-framework.readthedocs.io/en/v6.1.1/_modules/robot/api/interfaces.html)

### Inferences
- A locust-based Robot library should follow the HybridCore pattern: keyword methods on component classes, aggregated via PythonLibCore, giving both static discovery and dynamic dispatch.

### Gaps
- No concrete robotframework-locust or locust-Robot hybrid example found on GitHub; pattern must be adapted from PythonLibCore + SeleniumLibrary/RequestsLibrary conventions.