# Safety limits

Read these before you run a test against a host you do not own.
- **Peak user ceiling.** Run Load Test refuses a run before Locust starts when
  its peak user count is above `max_users` (default 100). The peak is the
  highest stage user count, or `users` when there are no stages, or the sum
  of the `fixed_count` values of the user classes if that sum is higher. To
  run more users, pass a higher `max_users` on purpose.
- **Host allowlist.** Create Load Test checks the host name against
  `allowed_hosts` (a comma list), or against the
  `LOCUSTLIBRARY_ALLOWED_HOSTS` environment variable when the argument is
  empty. A host that is not on the list is refused before any request. With
  no list set, the host is accepted and the log shows one warning.
- **Failure breaker.** `stop_on_fail_ratio` on Run Load Test, such as `20%`,
  stops the run when the share of failed requests goes over it. The check
  starts after `fail_ratio_warmup` (default 10s) and runs every half second.
  The log shows the reason as a warning. The default 0 turns it off.
- **Stop rules.** `Add Stop Rule    p95 > 1s for 10s` stops the run once the
  value stays over the limit for the whole window, checked every half second.
  Metrics: `pN` (Locust's current response time percentile, `ms` or `s`),
  `fail` (share of failed requests), `rcNNN` (share of responses whose code
  matches; `?` and `*` match digits), and `cpu` and `mem` (the load
  machine, so an overloaded generator stops the run instead of skewing it).
  `fail` and `rc` count only the requests since the last check; a check with
  no responses leaves the window as it is. By default a rule fails Run Load
  Test; end it with `, stop as passed` to only stop. The syntax follows
  Taurus pass/fail criteria.
- **Body check.** A server can answer 200 with an error page. Pass
  `expected_text` to Add Get Request or Add Post Request, and a response
  without that text counts as a failure.
- **No requests, no pass.** The Should keywords fail when the run, or the
  endpoint they check, recorded no requests.
- **Busy load generator.** When Locust sees this machine's CPU above 90%,
  Run Load Test logs a warning. Response times from such a run can be too
  high, because the generator itself is slow.
- **Web UI on loopback.** Start Locust Web binds 127.0.0.1 only. The keyword
  has no host argument, so other machines cannot reach the web UI through it.
- **Distributed mode stays on this machine.** Run Distributed binds the master
  and connects the workers on 127.0.0.1. It does not spread load across
  machines.
- **TLS checks.** `verify_tls=False` on Create Load Test skips certificate
  checks, as k6 insecureSkipTLSVerify does. Use it only for test hosts with a
  self-signed certificate.
- **Proxy.** Locust ignores HTTPS_PROXY, because it turns off trust_env. Pass
  the proxy to Create Load Test as an `http://` URL. The library sends both
  http and https traffic through it.
