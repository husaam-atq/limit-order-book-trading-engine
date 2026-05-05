"""Deterministic clock helpers for simulations and tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SimulationClock:
    """Simple monotonic clock used by deterministic simulations."""

    start: float = 0.0
    step: float = 1.0

    def __post_init__(self) -> None:
        if self.step <= 0:
            raise ValueError("Clock step must be positive.")
        self._time = float(self.start)

    @property
    def now(self) -> float:
        """Return the current simulation timestamp."""

        return self._time

    def tick(self, steps: int = 1) -> float:
        """Advance the clock and return the new timestamp."""

        if steps <= 0:
            raise ValueError("Clock tick steps must be positive.")
        self._time += self.step * steps
        return self._time

    def reset(self) -> None:
        """Reset the clock to the original start timestamp."""

        self._time = float(self.start)
