# Product

<!-- impeccable:product-schema 1 -->

## Platform

desktop (PySide6)

## Users

RF automation engineers, performance engineers, and CI/CD pipelines. They author and run load tests and gate releases on performance results.

## Product Purpose

A Robot Framework library that lets users define and run Locust load scenarios in RF syntax (no Python locustfile) and gate on results, with RF log reporting and Locust CSV/HTML export. Includes an optional PySide studio GUI for scenario building and live monitoring.

## Positioning

First-class RF-native authoring of load scenarios plus running existing locustfiles, with RF assertions and reports. Both surfaces are equally supported.

## Operating Context

Used in RF suites, CI pipelines, and optionally via the PySide studio GUI. Scenarios target HTTP endpoints; virtual users run in Locust greenlets.

## Capabilities and Constraints

- Define users, tasks (HTTP requests and arbitrary RF keywords), wait_time, on_start/on_stop in RF.
- Run headless with users, spawn_rate, run_time.
- Parse Locust stats; assertions on failures, percentiles, throughput, error rate.
- Export CSV/HTML reports alongside RF log.
- Web UI mode, distributed workers, PySide studio GUI included in MVP.
- Python >=3.11 (Locust requirement). Robot Framework >=7.5.
- RF-keyword tasks execute in greenlets; keywords must be greenlet-safe.

## Brand Commitments

None specified. Standard MIT license, PyPI publishing, RF conventions.

## Product Principles

- RF-native authoring first; Locust fidelity second.
- Headless by default; GUI optional extra.
- Small modules, TDD, measured behavior over assumptions.
- Greenlet safety documented, not hidden.

## Accessibility & Inclusion

Standard. GUI follows platform accessibility norms.
