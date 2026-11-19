# arXiv Load Testing, Concurrency, and Performance Regression Research

## Recent arXiv papers on load/performance testing tools and methodologies

### Takeaway
Recent arXiv work (2025-2026) treats load testing as an adaptive, feedback-driven search problem with open-loop request generation, hysteresis-based health assessment, and multi-metric SLO evaluation; general-purpose tools (Locust, JMeter, k6) are cited as lacking ML-specific abstractions, and coordinated omission remains a flagged measurement flaw.

### Cited Findings
- Vanguard (Meta) is an industrial adaptive load-testing framework: feedback-driven search with dampening (alpha=0.5), spike tolerance (tau=2), and convergence detection via coefficient of variation over the last 3 capacity estimates; open-loop request generation to avoid coordinated omission — [arXiv 2606.22013](https://arxiv.org/html/2606.22013v1).
- Workload calibration using recorded traffic reduced estimation error from ~30% to 2-6%; warmup handling improved accuracy by 22.2%; full Vanguard MAE 5.2% vs naive linear scaling 42.1% — [arXiv 2606.22013](https://arxiv.org/html/2606.22013v1).
- Health assessment uses five states (Healthy/Warn/Unhealthy/Critical/Overloaded) with weighted score H_score = sum(w_i * normalize(m_i, t_i)) and hysteresis (n=2 windows upward, n=3 downward); reported ~40% false-positive reduction — [arXiv 2606.22013](https://arxiv.org/html/2606.22013v1).
- Mesh2 integrates Locust as the primary distributed load generator for Kubernetes resilience evaluation in cloud-edge environments — [arXiv 2507.16109](https://arxiv.org/html/2507.16109v1).
- Load Testing for ML Model Serving identifies six lessons: workload representativeness dominates strategy sophistication; warmup handling highest-leverage; adaptive feedback prevents overshooting near nonlinear (dynamic batching) capacity cliffs; co-location effects significant but hard to reproduce; continuous testing catches regressions; health assessment needs hysteresis — [arXiv 2606.22013](https://arxiv.org/html/2606.22013v1).
- RELOAD: self-adaptive reinforcement-learning-driven load testing agent that learns optimal workload policy without system models or source code — [arXiv 2104.12893](https://arxiv.org/html/2104.12893v1).
- LLMRunner: closed-workload model performance testing framework for LLM servings with configurable multi-turn conversations and think-time distributions — [arXiv 2611.15372](https://arxiv.org/html/2611.15372v1).

### Inferences
- For a Locust-based tool, adopting open-loop generation and warmup exclusion is directly supported by cited evidence; coordinated omission is a real risk for closed-loop generators.
- Adaptive dampening near capacity cliffs is applicable to any nonlinear system, not only ML serving.

### Gaps
- No direct arXiv comparison of Locust vs k6/JMeter on identical workloads in 2022-2026 window found; claims of relative performance remain vendor-sourced.

## Research on greenlet/gevent-based concurrency and its limitations

### Takeaway
Greenlet/gevent provide cooperative, single-threaded concurrency that simplifies synchronous-style code but cannot use multiple cores, blocks the whole process on CPU-bound work, and interacts poorly with the GIL; free-threaded Python (3.13+) and GIL-removal trade-offs are active 2026 research topics.

### Cited Findings
- Greenlets use cooperative multitasking: a greenlet never yields except at explicit I/O or switch points, so CPU-bound work stalls all other greenlets — [Stack Overflow / gevent docs](https://stackoverflow.com/questions/50209009/why-the-amount-of-greenlets-will-impact-the-elapsed-time-of-the-responses).
- "The Sharp Edges of Gevent": the hub greenlet manages the runtime and must not perform I/O; violations corrupt scheduling — [Tigera blog](https://tigera.io/blog/the-sharp-edges-of-gevent).
- Greenlet 3.3+ supports free-threaded CPython builds but with limited testing and limitations — [greenlet.readthedocs.io](https://greenlet.readthedocs.io/en/stable/).
- GIL prevents multiple threads executing Python bytecode concurrently in one process, limiting multi-core utilization; Python 3.13+ introduces optional free-threaded builds (no-GIL) — [arXiv 2603.04782](https://arxiv.org/html/2603.04782v1).
- Under production-scale request rates (100s-1000s QPS), the Python GIL fundamentally throttles client service rate in LLM inference benchmarks — [arXiv 2605.24217](https://arxiv.org/html/2605.24217).

### Inferences
- Locust's gevent-based workers scale I/O-bound load well but CPU-heavy user code or JSON processing becomes a bottleneck shared across all greenlets; offloading CPU work to processes or using free-threaded Python may help.
- For high-QPS targets, client-side GIL contention is a measurable limiter independent of server capacity.

### Gaps
- No peer-reviewed benchmark quantifying greenlet overhead vs asyncio/trio for load generation specifically; available evidence is anecdotal/blog-level.

## Statistical methods for performance regression detection

### Takeaway
Performance regression detection research (2022-2026) favors change-point detection on time series, bootstrap confidence intervals, non-parametric tests, and tail-percentile (P90/P99) metrics over mean-based comparisons; sustained-violation (hysteresis) rules reduce false positives.

### Cited Findings
- "Evaluating Change Point Detection Methods for Software Performance Regression Analysis" (arXiv 2610.09023): a 10% difference in a single performance test run can mislead; time-series change-point detection preferred — [arXiv 2610.09023](https://arxiv.org/pdf/2610.09023v1).
- "Early Detection of Performance Regressions by Bridging Local..." (arXiv 2408.08148): statistical significance thresholds matter; developers rely on practical significance — [arXiv 2408.08148](https://arxiv.org/html/2408.08148v1).
- RMIT shrinks confidence interval width from 10.65% to 0.37% for FaaS performance change detection — [arXiv 2311.03889](https://arxiv.org/html/2311.03889v1).
- Critical-Path-Aware Pattern Analysis (arXiv 2609.17179) builds statistical performance models for regression detection by triangulating critical paths — [arXiv 2609.17179](https://arxiv.org/html/2609.17179v1).
- Steady-state detection kernel approach for warmup-to-steady transition in metric time series — [arXiv 2506.04204](https://arxiv.org/html/2506.04204v1).
- Vanguard uses non-parametric tests, ICC for reproducibility, Bland-Altman for agreement, 95% bootstrap CIs (10,000 resamples), multivariate regression on error factors — [arXiv 2606.22013](https://arxiv.org/html/2606.22013v1).

### Inferences
- Percentile-based (P90) capacity definitions align with SLO practice and are more robust than means for skewed latency.
- Sustained-violation rules (n consecutive windows) are a practical form of hysteresis for flapping prevention.

### Gaps
- No single canonical statistical test for performance regression across heterogeneous workloads; method choice remains context-dependent.

## Distributed load testing architectures

### Takeaway
Distributed load testing architectures separate a controller/strategy engine from stateless worker agents pulling jobs from a queue with atomic dequeue, aggregate metrics over windows, and provision capacity on demand; Locust's own master/worker model is the de-facto reference cited in academic work.

### Cited Findings
- Vanguard architecture: Task Orchestrator (worker) with atomic dequeue from Model Tests Queue; Strategy Engine with pluggable strategies; Metrics Collector aggregating latency percentiles/throughput/error rates over windows; Metrics Health Assessor; Capacity Allocator for static/dynamic GPU provisioning; Telemetry Logger — [arXiv 2606.22013](https://arxiv.org/html/2606.22013v1).
- Mesh2 combines Kubernetes fault injection with Locust distributed load generation for realistic concurrent workload simulation — [arXiv 2507.16109](https://arxiv.org/html/2507.16109v1).
- Locust cited as supporting distributed testing over multiple machines to simulate millions of simultaneous users — [locust.io](https://locust.io/).

### Inferences
- Atomic job dequeue and idempotent workers are essential for reliable distributed runs; metric aggregation should be windowed to avoid noise.
- Capacity allocation (static vs dynamic) is a distinct concern from load generation and should be pluggable.

### Gaps
- No arXiv paper found benchmarking Locust master/worker scaling limits (max users per worker, network overhead) in 2022-2026.