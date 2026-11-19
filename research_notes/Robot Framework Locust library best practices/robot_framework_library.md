# Robot Framework Locust Library Best Practices

## RF Library Architecture: Static vs Dynamic vs Hybrid

### Takeaway
Choose static API for simple libraries, Hybrid/Dynamic (via robotlibcore) for larger ones needing keyword components, plugins, translation, or runtime keyword generation.

### Cited Findings
- Static API: library is a class/module; public methods become keywords automatically. Simplest approach. — [RF User Guide 7.5.1, Creating test libraries](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-libraries)
- Dynamic API: library implements `get_keyword_names` and `run_keyword`; RF calls them at runtime. Allows dynamic keyword lists and metadata. — [Dynamic library API](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#dynamic-library-api)
- Hybrid API: methods exposed like static, but metadata via optional `get_keyword_arguments`/`get_keyword_documentation` etc. — [RF User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- robotlibcore (`DynamicCore`/`HybridCore`) handles the API boilerplate: keyword components, `@keyword` decorator, plugins, listeners, translations. Used by SeleniumLibrary, Browser. — [PythonLibCore README](https://github.com/robotframework/PythonLibCore/blob/main/README.md)
- Python 3.11+/RF 7.x supported; RF core requires Python 3.8+. — [RF User Guide install](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)

### Inferences
- For robotframework-locust, a HybridCore/DynamicCore library with component classes (Users, LoadTest, Stats) is appropriate given multiple concerns.

### Gaps
- None notable.

## Keyword Naming Conventions, Arguments, Type Hints, Defaults, Embedded Args

### Takeaway
Use Title Case keyword names, type hints for auto-conversion, sensible defaults, `@keyword` decorator for name/tags, avoid embedded args unless needed.

### Cited Findings
- Keyword names use spaces between words; method names use underscores converted. — [RF User Guide creating keywords](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-keywords)
- `@keyword(name=..., tags=[...])` decorator sets name/tags. — [robot.api.deco](https://robot-framework.readthedocs.io/en/stable/autodoc/robot.api.html)
- Type hints in RF 7.0+ drive automatic argument conversion; `TypeInfo` added in 7.0. — [RF docs autodoc](https://robot-framework.readthedocs.io/en/stable/autodoc/robot.api.html)
- Embedded arguments in keyword name supported for user keywords; library keywords generally avoid. — [RF User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- RPA style guide recommends documenting args/returns/exceptions. — [RF style guide](https://docs.robotframework.org/docs/style_guide)

### Inferences
- Add type hints to all keyword params; document return values.

### Gaps
- Exact arg count limits not found.

## State Management: Scope, Instance State, Thread/Greenlet Safety

### Takeaway
Default scope is TEST (new instance per test); use SUITE/GLOBAL for shared state but add cleanup keywords; RF is not thread-safe; avoid global mutable state.

### Cited Findings
- `ROBOT_LIBRARY_SCOPE` can be TEST (default), SUITE (TEST SUITE), GLOBAL. — [RF User Guide Creating test libraries](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#creating-test-libraries)
- SUITE/GLOBAL with state: recommend cleanup keywords. — [RF User Guide](http://robotframework.org/robotframework/4.1.2/RobotFrameworkUserGuide.html)
- RF is not multi-threaded/thread-safe; each keyword entry/exit registered in output.xml. — [RF forum multithreading](https://forum.robotframework.org/t/robot-framework-multithreading/5050)
- Global scope instance created once; importing again doesn't replace. — [RF forum global scope](https://forum.robotframework.org/t/loading-libraries-to-global-scope/497)

### Inferences
- For locust load tests, use a suite/global scope with explicit Reset/Cleanup keyword; locust's gevent greenlets require care—keep RF calls on main thread.

### Gaps
- Locust-specific greenlet safety guidance not found in sources.

## Documentation: libdoc, Docstrings, Tags, Deprecation

### Takeaway
Write RF-format docstrings; use `@keyword(tags=...)`; deprecate via documentation and `@keyword`? Use libdoc to generate docs; Markdown/RF format supported.

### Cited Findings
- Libdoc generates docs from docstrings; supports RF format and Markdown. — [RF User Guide Libdoc](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#library-documentation-tool-libdoc)
- Arguments, return values, exceptions, tags documented. — [RF User Guide libdoc](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- Deprecation: RF supports deprecated keywords via documentation conventions? (not fully specified in fetched sources) — [RF User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)

### Inferences
- Use `@keyword` tags for categorization; keep docstrings RF-formatted.

### Gaps
- Official deprecation decorator details not confirmed from sources.

## Testing RF Libraries: Unit vs Acceptance, pabot

### Takeaway
Unit-test Python logic with pytest/unittest; acceptance-test keywords via .robot suites; use pabot for parallel execution; run in Alpine CI for Robot repos.

### Cited Findings
- Acceptance tests are .robot files exercising keywords. — [RF User Guide](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html)
- pabot splits execution into parallel processes. — [pabot README](https://github.com/mkorpela/pabot/blob/main/README.md)
- pytest-robotframework plugin exists. — [PyPI pytest_robotframework](https://pypi.org/project/pytest_robotframework/)

### Inferences
- Provide both unit tests (fast) and .robot acceptance tests.

### Gaps
- robotframework-testing specifics not found.

## Packaging for RF Ecosystem: Entry Points, Naming, Classifiers

### Takeaway
Name package `robotframework-<name>`; use pyproject.toml; add Framework :: Robot Framework classifier; installable via pip automatically.

### Cited Findings
- Test libraries packaged via Python packaging auto-install and importable. — [RF User Guide distributing](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#distributing-test-libraries)
- PyPI classifiers include Framework :: Robot Framework. — [pypi classifiers gist](https://gist.github.com/nazrulworld/3800c84e28dc464b2b30cec8bc1287fc)

### Inferences
- Use `robotframework-locust` naming; classifiers Framework :: Robot Framework.

### Gaps
- Console entry points optional; not required.

## Common Pitfalls: Global State, Side Effects, Logging

### Takeaway
Avoid module-level mutable state; clean up between tests; use `robot.api.logger` not print; handle RF timeouts; avoid side effects in keyword discovery.

### Cited Findings
- Libraries as listeners need careful state. — [PythonLibCore README listener](https://github.com/robotframework/PythonLibCore/blob/main/README.md)
- RF timeouts handling documented. — [RF User Guide timeouts](https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#handling-robot-framework-s-timeouts)

### Inferences
- Use RF logger; ensure idempotent cleanup.

### Gaps
- Specific logging best practice doc not cited.