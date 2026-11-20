# Changelog

## 0.1.0 (unreleased)

- Add User Class starts a user class with its own tasks, wait time, weight and
  fixed user count. One class maps to one k6 scenario. (b01685d)
- Set Load Stages ramps users over `duration:users` stages, moving linearly.
  Run Load Test takes `iterations`, a task budget shared by all users. (5e62482)
- Create Load Test takes `verify_tls` and `proxy`. The proxy goes straight to
  the client, because Locust ignores HTTPS_PROXY. Should Meet Error Rate takes
  an endpoint name. (973f485)
- Add Python Task calls a `module.function` with the Locust user, so each
  request in a flow gets its own stats row. (7b7b003)
- Add Get Request and Add Post Request take headers, a JSON or form body, and
  `expected_status` (one code, a comma list or a list; default 200). Only the
  listed codes pass. Before, Locust's default (4xx and 5xx fail) applied.
  (be353d3)
- Run Load Test takes `max_users` (default 100). A run whose peak user count
  is above it is refused before Locust starts. (044f1cb)
