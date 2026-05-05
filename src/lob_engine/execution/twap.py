"""Time-weighted average price execution schedule."""

from __future__ import annotations

import numpy as np
import pandas as pd

from lob_engine.execution.base import ExecutionAlgorithm, allocate_integer_quantity, schedule_frame, time_grid


class TWAPExecutor(ExecutionAlgorithm):
    """Split a parent order evenly across a fixed number of time slices."""

    name = "TWAP"

    def __init__(self, parent_order, slices: int = 10) -> None:
        super().__init__(parent_order)
        if slices <= 0:
            raise ValueError("TWAP slices must be positive.")
        self.slices = min(slices, parent_order.quantity)

    def build_schedule(self) -> pd.DataFrame:
        timestamps = time_grid(self.parent_order.start_time, self.parent_order.end_time, self.slices)
        quantities = allocate_integer_quantity(self.parent_order.quantity, np.ones(self.slices))
        return schedule_frame(self.parent_order, self.name, timestamps, quantities)
