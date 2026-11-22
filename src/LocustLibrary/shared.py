"""Values one load test step hands to another during a run, like rfswarm's TestDataTable."""

from gevent.queue import Empty, Full, Queue
from robot.api.deco import keyword

from . import users
from .parsing import _parse_seconds


class SharedKeywords:
    _shared: dict[str, Queue]
    _shared_limit: int

    def _queue(self, name: str) -> Queue:
        if name not in self._shared:
            self._shared[name] = Queue(maxsize=self._shared_limit or None)
        return self._shared[name]

    @keyword
    def put_shared_value(self, name: str, value: object) -> None:
        """Add `value` under `name` for another user's step to take, such as a created id.

        A name holds at most the library's `shared_limit` values (0 is no limit); one more fails.
        """
        try:
            self._queue(name).put_nowait(value)
        except Full:
            raise AssertionError(
                f"Shared value '{name}' is full at {self._shared_limit} values") from None

    @keyword
    def take_shared_value(self, name: str, timeout: str = "10s") -> object:
        """Take the oldest value under `name`, waiting up to `timeout` for one to be put.

        Each value goes to one taker only. With none in time the keyword fails, so the task
        counts as a failure, and inside a run the wait shows in the stats as a failed
        `SHARED` request. Run Load Test starts with no values.
        """
        seconds = _parse_seconds(timeout)
        try:
            return self._queue(name).get(timeout=seconds)
        except Empty:
            error = AssertionError(f"No shared value '{name}' within {seconds:g} s")
            user = getattr(users._running, "user", None)
            if user is not None:
                user.environment.events.request.fire(
                    request_type="SHARED", name=f"Take Shared Value {name}",
                    response_time=seconds * 1000, response_length=0, exception=error)
            raise error from None
