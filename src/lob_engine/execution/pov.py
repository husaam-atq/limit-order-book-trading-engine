"""Participation-of-volume execution schedule."""

from __future__ import annotations

import numpy as np
import pandas as pd

from lob_engine.execution.base import ExecutionAlgorithm, schedule_frame, time_grid


class POVExecutor(ExecutionAlgorithm):
    """Execute up to a target percentage of observed market volume."""

    name = "POV"

    def __init__(self, parent_order, market_volumes: list[int] | np.ndarray, participation_rate: float = 0.1) -> None:
        super().__init__(parent_order)
        if not 0 < participation_rate <= 1:
            raise ValueError("Participation rate must be in (0, 1].")
        if len(market_volumes) == 0:
            raise ValueError("Market volume path cannot be empty.")
        self.market_volumes = np.asarray(market_volumes, dtype="int64")
        if np.any(self.market_volumes < 0):
            raise ValueError("Market volumes cannot be negative.")
        self.participation_rate = participation_rate

    def build_schedule(self) -> pd.DataFrame:
        timestamps = time_grid(self.parent_order.start_time, self.parent_order.end_time, len(self.market_volumes))
        remaining = self.parent_order.quantity
        quantities: list[int] = []
        for volume in self.market_volumes:
            if remaining <= 0:
                quantities.append(0)
                continue
            target = int(np.floor(volume * self.participation_rate))
            child_qty = min(max(target, 0), remaining)
            quantities.append(child_qty)
            remaining -= child_qty
        schedule = schedule_frame(self.parent_order, self.name, timestamps, quantities)
        if not schedule.empty:
            non_zero_volumes = [v for v, q in zip(self.market_volumes, quantities) if q > 0]
            schedule["market_volume"] = non_zero_volumes
            schedule["target_participation"] = self.participation_rate
            schedule["actual_participation"] = schedule["quantity"] / schedule["market_volume"].replace(0, np.nan)
        return schedule
