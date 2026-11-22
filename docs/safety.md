# Safety limits

Read these before you run a test against a host you do not own.
The ceiling, allowlist, breaker and stop rules apply to Create Load Test and
Run Load Test, which Studio's Build tab also calls. Start Locust Web and Run
Distributed run your locustfile as it is. Both check the host; only Run
Distributed checks the user count, and only when you pass `users` (see
below). They have no breaker and no stop rules.

## Contents

- [Limits before the run](#limits-before-the-run)
- [Limits during the run](#limits-during-the-run)
- [Checks on the results](#checks-on-the-results)
- [Notes on trust and network](#notes-on-trust-and-network)

## Limits before the run

- **Peak user ceiling.** Run Load Test always checks the peak user count. It refuses a run before Locust starts when
  its peak user count is above `max_users` (default 100). The peak is the
  highest stage user count, or `users` when there are no stages, or the sum
  of the `fixed_count` values of the user classes if that sum is higher. To
  run more users, pass a higher `max_users` on purpose.
- **Host allowlist.** Create Load Test checks the host name against
  `allowed_hosts` (a comma list), or against the
  `LOCUSTLIBRARY_ALLOWED_HOSTS` environment variable when the argument is
  empty. Spaces around each name are dropped. The match is exact and ignores
  case and the port: with `allowed_hosts=api.example.com`, the host
  `https://API.example.com:8443` is accepted, but `https://v2.api.example.com`
  is refused, because subdomains do not match. A host that is not on the list
  is refused before any request. With no list set, the host is accepted and
  the log shows one warning.
- **Web UI and distributed runs.** Start Locust Web and Run Distributed take
  an optional `host` and `allowed_hosts`. The host is checked the same way
  as in Create Load Test. Run Distributed also takes `users`, and refuses a
  count above `max_users` (default 100). It checks this only when you pass
  `users`; without it, the locustfile and web UI set the count, with no
  ceiling. Start Locust Web has no user ceiling.
- **Generated suites set these limits by default.** A suite that `rflocust-k6` writes
  sets `allowed_hosts=${ALLOWED_HOSTS}` on Create Load Test. The detected
  host goes into the variables file. The run keyword adds the stop rules
  `fail > 10% for 30s` and `idle > 30s`, and Run Load Test gets
  `stop_on_fail_ratio=20%`. The report shows a `safety | default` row.

## Limits during the run

- **Failure breaker.** `stop_on_fail_ratio` on Run Load Test, such as `20%`,
  stops the run when the share of failed requests goes over it. The check
  starts after `fail_ratio_warmup` (default 10s) and runs every half second.
  The log shows the reason as a warning. A breaker stop fails Run Load Test,
  as a stop rule does. Pass `breaker_fails=False` to stop the run but let it
  pass. The default 0 turns the breaker off.
- **Stop rules.** `Add Stop Rule    p95 > 1s for 10s` stops the run once the
  value stays over the limit for the whole window, checked every half second.
  The only operator is `>`. The window (`for 10s`) is optional; without it,
  one check over the limit is enough. Metrics and their units:
  - `pN`: response time percentile of all requests in the last 10 seconds
    (Locust's current percentile), in `ms` or `s`. A limit with no unit is
    read as milliseconds, so `p95 > 1` means 1 ms.
    `p95` is the 95th percentile. `p999` and `p99.9` both mean the 99.9th.
  - `fail`: share of failed requests, in `%`.
  - `rcNNN`: share of responses whose code matches, in `%`; `?` and `*`
    match digits. Example: `rc5?? > 1% for 5s`.
  - `cpu`: CPU use of the load machine, in `%`. Example: `cpu > 90% for 10s`.
  - `mem`: memory use of the load machine, in `%`. Example: `mem > 85% for 10s`.
  - `idle`: time since the last completed response, in `ms` or `s` (the
    unit is required). Before the first response, it counts from the run
    start. Example: `idle > 30s` stops a run that gets no answers for 30 seconds.

  The `cpu` and `mem` rules let an overloaded generator stop the run instead
  of skewing it. A `cpu` or `mem` stop fails Run Load Test by default, even
  though the cause is the load machine, not the target; add
  `, stop as passed` if you do not want that.

  `fail` and `rc` take each value from the requests completed since the
  previous check (half a second earlier). A check with no new responses
  gives no value: the rule's time over the limit neither grows nor starts
  again. Example: with `fail > 10% for 30s`, the rule stops the run once
  each check with responses has shown over 10% for 30 seconds in a row. A
  check at or under the limit starts the count again. By default a rule
  fails Run Load Test; end it with `, stop as passed` to only stop. The
  syntax follows the pass/fail criteria of Taurus, an open source load test
  runner ([Taurus pass/fail criteria](https://gettaurus.org/docs/PassFailCriteria/)).
- **Busy load generator.** When Locust sees this machine's CPU above 90%,
  Run Load Test logs a warning, and the run can still pass: the Should
  keywords do not look at this warning. Pass `fail_on_busy_cpu=True` to fail
  the run instead. Response times from such a run can be too
  high, because the generator itself is slow. Lower the user count, or move
  the run to a larger machine, before you trust the response times.
- **Shared value limit.** One Put Shared Value name holds at most
  `shared_limit` values (library import argument, default 10000; 0 is no
  limit). One more value fails. When Take Shared Value times out in a run, it
  is a failed SHARED request named `Take Shared Value <name>`.

## Checks on the results

- **Body check.** A server can answer 200 with an error page. Pass
  `expected_text` to Add Get Request or Add Post Request, and a response
  without that text counts as a failure.
- **No requests, no pass.** The Should keywords fail when the run, or the
  endpoint they check, recorded no requests.

## Notes on trust and network

- **Code that runs.** Add Python Task imports the module you name and runs
  its function. The k6 converter runs `k6 inspect`, which runs the script's
  init code, so `rflocust-k6` refuses to run it without `--trust-script`.
  Open suite in Studio reads the suite with a Robot dry run, which
  imports every Python library and variable file the suite names and so runs
  their module code. Use these only with code and suites you trust.
- **Web UI on loopback.** Start Locust Web binds 127.0.0.1 only, so other
  machines cannot reach the web UI. Its `host` argument sets the target, not
  the bind address.
- **Distributed mode stays on this machine.** Run Distributed binds the master
  and connects the workers on 127.0.0.1. It does not spread load across
  machines.
- **Robot log masking.** The calls that Run Load Test writes to the Robot log
  (`log.html`) are masked. It masks the Authorization,
  Proxy-Authorization, Cookie and Set-Cookie headers. It also masks the body
  fields password, client_secret, access_token, refresh_token, id_token and
  otp. URLs, query strings, other headers and other body fields are logged as
  sent. Do not put secrets in URLs.
- **TLS checks.** `verify_tls=False` on Create Load Test skips certificate
  checks, as k6 insecureSkipTLSVerify does. Use it only for test hosts with a
  self-signed certificate.
- **Proxy.** Locust ignores the HTTPS_PROXY environment variable, so set the
  proxy here instead. Pass it to Create Load Test as an `http://` URL. The library does not check
  the value, so a wrong one fails only when the requests are sent. The
  library sends both http and https traffic through it.
