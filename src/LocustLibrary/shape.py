"""k6 ramp stages as a Locust load shape."""

from locust import LoadTestShape

from .scenario import Stage

__all__ = ["Stage", "StageShape"]


class StageShape(LoadTestShape):
    """Move linearly to each stage's user count over that stage, as k6 ramping-vus does."""

    def __init__(self, stages: list[Stage]) -> None:
        super().__init__()  # type: ignore[no-untyped-call]
        self._ends: list[tuple[float, int, float]] = []
        elapsed, previous = 0.0, 0
        for stage in stages:
            elapsed += stage.seconds
            change = abs(stage.users - previous)
            rate = change / stage.seconds if change and stage.seconds else 1.0
            self._ends.append((elapsed, stage.users, rate))
            previous = stage.users

    @property
    def total(self) -> float:
        return self._ends[-1][0] if self._ends else 0.0

    def tick(self) -> tuple[int, float] | None:
        now = self.get_run_time()  # type: ignore[no-untyped-call]
        for end, users, rate in self._ends:
            if now < end:
                return users, rate
        return None
