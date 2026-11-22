# Safety limits

Read these before you run a test against a host you do not own.
The ceiling, allowlist, breaker and stop rules apply to Create Load Test and
Run Load Test, which Studio's run tab also calls. Start Locust Web and Run
Distributed run your locustfile as it is, with none of these limits.

## Contents

- [Limits before the run](#limits-before-the-run)
- [Limits during the run](#limits-during-the-run)
- [Checks on the results](#checks-on-the-results)
- [Notes on trust and network](#notes-on-trust-and-network)

## Limits before the run

- **Peak user ceiling.** Run Load Test refuses a run before Locust starts when
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

## Limits during the run

- **Failure breaker.** `stop_on_fail_ratio` on Run Load Test, such as `20%`,
  stops the run when the share of failed requests goes over it. The check
  starts after `fail_ratio_warmup` (default 10s) and runs every half second.
  The log shows the reason as a warning. A run the breaker stops does not
  fail Run Load Test; only a stop rule does that. The default 0 turns it off.
- **Stop rules.** `Add Stop Rule    p95 > 1s for 10s` stops the run once the
  value stays over the limit for the whole window, checked every half second.
  The only operator is `>`. The window (`for 10s`) is optional; without it,
  one check over the limit is enough. Metrics and their units:
  - `pN`: Locust's current response time percentile, in `ms` or `s`.
    `p95` is the 95th percentile. `p999` and `p99.9` both mean the 99.9th.
  - `fail`: share of failed requests, in `%`.
  - `rcNNN`: share of responses whose code matches, in `%`; `?` and `*`
    match digits. Example: `rc5?? > 1% for 5s`.
  - `cpu`: CPU use of the load machine, in `%`. Example: `cpu > 90% for 10s`.
  - `mem`: memory use of the load machine, in `%`. Example: `mem > 85% for 10s`.

  The `cpu` and `mem` rules let an overloaded generator stop the run instead
  of skewing it. `fail` and `rc` count only the requests since the last
  check; a check with no responses leaves the window as it is. By default a
  rule fails Run Load Test; end it with `, stop as passed` to only stop. The
  syntax follows the pass/fail criteria of Taurus, an open source load test
  runner ([Taurus pass/fail criteria](https://gettaurus.org/docs/PassFailCriteria/)).
- **Busy load generator.** When Locust sees this machine's CPU above 90%,
  Run Load Test logs a warning. Response times from such a run can be too
  high, because the generator itself is slow. Lower the user count, or move
  the run to a larger machine, before you trust the response times.

## Checks on the results

- **Body check.** A server can answer 200 with an error page. Pass
  `expected_text` to Add Get Request or Add Post Request, and a response
  without that text counts as a failure.
- **No requests, no pass.** The Should keywords fail when the run, or the
  endpoint they check, recorded no requests.

## Notes on trust and network

- **Code that runs.** Add Python Task imports the module you name and runs
  its function. The k6 converter runs `k6 inspect`, which runs the script's
  init code. Open suite in Studio reads the suite with a Robot dry run, which
  imports every Python library and variable file the suite names and so runs
  their module code. Use these only with code and suites you trust.
- **Web UI on loopback.** Start Locust Web binds 127.0.0.1 only. The keyword
  has no host argument, so other machines cannot reach the web UI through it.
- **Distributed mode stays on this machine.** Run Distributed binds the master
  and connects the workers on 127.0.0.1. It does not spread load across
  machines.
- **Request log masking.** The request log masks the Authorization,
  Proxy-Authorization, Cookie and Set-Cookie headers. It also masks the body
  fields password, client_secret, access_token, refresh_token, id_token and
  otp. URLs, query strings, other headers and other body fields are logged as
  sent. Do not put secrets in URLs.
- **TLS checks.** `verify_tls=False` on Create Load Test skips certificate
  checks, as k6 insecureSkipTLSVerify does. Use it only for test hosts with a
  self-signed certificate.
- **Proxy.** Locust ignores the HTTPS_PROXY environment variable, so set the
  proxy here instead. Pass it to Create Load Test as an `http://` URL. The
  library sends both http and https traffic through it.
