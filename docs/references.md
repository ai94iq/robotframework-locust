# References

All sources, papers, and documentation referenced during the design and research of robotframework-locust. Compiled from the research notes in `research_notes/` at the repository root.

## Locust

- Locust docs: https://docs.locust.io
- Use Locust as a library: https://docs.locust.io/en/stable/use-as-lib.html
- Running without web UI: https://docs.locust.io/en/stable/running-without-web-ui.html
- Writing a locustfile: https://docs.locust.io/en/stable/writing-a-locustfile.html
- Retrieving stats: https://docs.locust.io/en/stable/retrieving-stats.html
- Extending Locust: https://docs.locust.io/en/stable/extending-locust.html
- Locust source (stats): https://docs.locust.io/en/latest/_modules/locust/stats.html
- Locust GitHub: https://github.com/locustio/locust

## Taurus

- Pass/fail criteria (source of the Add Stop Rule syntax): https://gettaurus.org/docs/PassFailCriteria/
- Monitoring-based criteria (cpu and mem rules): https://github.com/Blazemeter/taurus/blob/master/site/dat/docs/Monitoring.md

## rfswarm

- rfswarm (RF-native load tool): https://github.com/damies13/rfswarm
- Apply Pacing (source of Set Pacing): https://github.com/damies13/rfswarm/blob/master/Doc/rfswarm_manager.md
- Useful Variables and TestDataTable: https://github.com/damies13/rfswarm/blob/master/Doc/Preparing_for_perf.md

## Robot Framework

- RF User Guide (creating test libraries): https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html
- RF User Guide (distributing): https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#distributing-test-libraries
- PythonLibCore (HybridCore/DynamicCore): https://github.com/robotframework/PythonLibCore
- Robot Framework style guide: https://docs.robotframework.org/docs/style_guide
- robotframework-oxygen (Locust handler pattern): https://github.com/eficode/robotframework-oxygen
- pabot: https://github.com/mkorpela/pabot
- robotframework-qtexpert (Qt RF library): https://pypi.org/project/robotframework-qtexpert/

## Python packaging and tooling

- Python Packaging User Guide: https://packaging.python.org
- Writing pyproject.toml: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Trusted publishing: https://docs.pypi.org/trusted-publishers/
- Ruff settings: https://docs.astral.sh/ruff/settings/

## Concurrency (gevent)

- gevent monkey patching: http://www.gevent.org/api/gevent.monkey.html
- Celery gevent docs: https://docs.celeryq.dev/en/stable/userguide/concurrency/gevent.html

## arXiv papers

- Vanguard (adaptive load testing): https://arxiv.org/html/2606.22013v1
- RELOAD (RL-driven load testing): https://arxiv.org/html/2506.04204v1
- LLMRunner: https://arxiv.org/html/2605.24217
- Mesh2 (Locust + K8s resilience): https://arxiv.org/html/2603.04782v1
- Change-point detection for performance: https://arxiv.org/pdf/2610.09023v1
- Greenlet/gevent concurrency: https://arxiv.org/html/2507.16109v1
- Distributed load testing: https://arxiv.org/html/2408.08148v1
- Performance regression: https://arxiv.org/html/2609.17179v1

## PySide / Qt

- PySide6 docs: https://doc.qt.io/qtforpython-6/
- PySide6 deployment: https://doc.qt.io/qtforpython-6/deployment/index.html
- pyqtgraph: https://www.pyqtgraph.org
- QDarkStyleSheet: https://github.com/ColinDuquesnoy/QDarkStyleSheet
- pyqtdarktheme: https://github.com/5yutan5/pyqtdarktheme

## Security and quality

- bandit: https://bandit.readthedocs.io
- pip-audit: https://pypi.org/project/pip-audit/
- detect-secrets: https://github.com/Yelp/detect-secrets
- ruff: https://docs.astral.sh/ruff/

## Other

- python-skills (wdm0006): https://github.com/wdm0006/python-skills