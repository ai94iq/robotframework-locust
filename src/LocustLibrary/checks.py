"""Keywords that read and assert on the stats of the last run."""

import html
from pathlib import Path

from robot.api import logger
from robot.api.deco import keyword

from .parsing import _measured_percentile, _parse_seconds
from .scenario import Stats, StatsRow


def _output_dir() -> str | None:
    """Robot's output folder, so reports land beside log.html; None outside a Robot run."""
    from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError

    try:
        return str(BuiltIn().get_variable_value("${OUTPUT DIR}"))
    except RobotNotRunningError:
        return None


class CheckKeywords:
    """Keywords that read the last run's stats and fail on a missed target."""

    _stats: Stats | None

    @keyword
    def get_locust_stats(self) -> dict[str, object]:
        """Return parsed stats as a dict."""
        if self._stats is None:
            return {}
        return {"rows": [r.__dict__ for r in self._stats.rows],
                "aggregated": self._stats.aggregated.__dict__ if self._stats.aggregated else None,
                "fail_ratio": self._stats.fail_ratio}

    @keyword
    def get_aggregated_stats(self) -> dict[str, object]:
        """Return aggregated stats."""
        if self._stats is None or self._stats.aggregated is None:
            return {}
        return self._stats.aggregated.__dict__

    def _aggregated(self) -> StatsRow:
        stats = self._stats
        if stats is None or stats.aggregated is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        if stats.aggregated.request_count == 0:
            raise RuntimeError("No requests recorded.")
        return stats.aggregated

    @keyword
    def should_have_no_failures(self) -> None:
        """Fail if any request failed."""
        row = self._aggregated()
        if row.failure_count > 0:
            raise AssertionError(f"Failures: {row.failure_count}")

    @keyword
    def should_meet_response_time(self, endpoint: str, percentile: str,
                                  maximum: str) -> None:
        """Assert response time percentile <= maximum."""
        if self._stats is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        if maximum.lower().endswith("ms"):
            max_ms = float(maximum.lower().rstrip("ms"))
        else:
            max_ms = _parse_seconds(maximum) * 1000
        # One name can hold several methods; the slowest one decides.
        targets = [r for r in self._stats.rows if r.name == endpoint]
        if not targets and self._stats.aggregated and endpoint.lower() in ("aggregated", "total", ""):
            targets = [self._stats.aggregated]
        if not targets:
            raise RuntimeError(f"Endpoint not found: {endpoint}")
        actual = max(_measured_percentile(r, percentile) for r in targets)
        if actual > max_ms:
            raise AssertionError(
                f"{endpoint} {percentile}={actual}ms > {max_ms}ms"
            )

    @keyword
    def should_meet_throughput(self, minimum: str) -> None:
        """Assert RPS >= minimum."""
        row = self._aggregated()
        min_rps = float(minimum)
        if row.rps < min_rps:
            raise AssertionError(f"RPS {row.rps} < {min_rps}")

    @keyword
    def should_meet_error_rate(self, maximum: str, endpoint: str = "") -> None:
        """Assert error rate <= maximum percent, overall or for one endpoint."""
        rows = self._endpoint_rows(endpoint) if endpoint else [self._aggregated()]
        max_rate = float(maximum.rstrip("%")) / 100.0
        rate = sum(r.failure_count for r in rows) / sum(r.request_count for r in rows)
        if rate > max_rate:
            raise AssertionError(f"{rows[0].name} error rate {rate:.2%} > {max_rate:.2%}")

    def _endpoint_rows(self, endpoint: str) -> list[StatsRow]:
        # One name can hold several methods; k6 thresholds count them together.
        rows = [r for r in (self._stats.rows if self._stats else []) if r.name == endpoint]
        if not rows:
            raise RuntimeError(f"Endpoint not found: {endpoint}")
        if sum(r.request_count for r in rows) == 0:
            raise RuntimeError("No requests recorded.")
        return rows

    @keyword
    def export_report(self, base_path: str = "locust") -> str:
        """Write <base>_stats.csv and the Locust HTML report <base>.html beside log.html.

        The HTML report is linked in the log. Returns the base path.
        """
        if self._stats is None:
            raise RuntimeError("No stats available. Run Load Test first.")
        from .reporting import write_stats_csv

        base = write_stats_csv(self._stats, base_path, _output_dir())
        if self._stats.report_html:
            Path(base + ".html").write_text(self._stats.report_html, encoding="utf-8")
            name = html.escape(Path(base).name + ".html")
            logger.info(f'Locust report: <a href="{name}">{name}</a>', html=True)
        return base
