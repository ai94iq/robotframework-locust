"""Values one load test step hands to another during a run, like rfswarm's TestDataTable."""

from gevent.queue import Empty, Queue
from robot.api.deco import keyword

from .parsing import _parse_seconds


class SharedKeywords:
    _shared: dict[str, Queue]

    @keyword
    def put_shared_value(self, name: str, value: object) -> None:
        """Add `value` under `name` for another user's step to take, such as a created id."""
        self._shared.setdefault(name, Queue()).put(value)

    @keyword
    def take_shared_value(self, name: str, timeout: str = "10s") -> object:
        """Take the oldest value under `name`, waiting up to `timeout` for one to be put.

        Each value goes to one taker only. With none in time the keyword fails, so the task
        counts as a failure. Run Load Test starts with no values.
        """
        seconds = _parse_seconds(timeout)
        try:
            return self._shared.setdefault(name, Queue()).get(timeout=seconds)
        except Empty:
            raise AssertionError(f"No shared value '{name}' within {seconds:g} s") from None
