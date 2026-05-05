"""Implementation shortfall execution schedule."""

from __future__ import annotations

import numpy as np
import pandas as pd

from lob_engine.execution.base import ExecutionAlgorithm, allocate_integer_quantity, schedule_frame, time_grid


class ImplementationShortfallExecutor(ExecutionAlgorithm):
    """Front-load execution according to a configurable urgency parameter."""

    name = "ImplementationShortfall"

    def __init__(self, parent_order, slices: int = 10, urgency: float = 0.5) -> None:
        super().__init__(parent_order)
        if slices <= 0:
            raise ValueError("Implementation shortfall slices must be positive.")
        if not 0 <= urgency <= 1:
            raise ValueError("Urgency must be between 0 and 1.")
        self.slices = min(slices, parent_order.quantity)
        self.urgency = urgency

    def build_schedule(self) -> pd.DataFrame:
        timestamps = time_grid(self.parent_order.start_time, self.parent_order.end_time, self.slices)
        if self.slices == 1:
            weights = np.array([1.0])
        else:
            positions = np.linspace(0, 1, self.slices)
            decay = 1.0 + 5.0 * self.urgency
            weights = np.exp(-decay * positions)
        quantities = allocate_integer_quantity(self.parent_order.quantity, weights)
        schedule = schedule_frame(self.parent_order, self.name, timestamps, quantities)
        if not schedule.empty:
            schedule["urgency"] = self.urgency
        return schedule
