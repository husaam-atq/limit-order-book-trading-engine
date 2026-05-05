"""Volume-weighted average price execution schedule."""

from __future__ import annotations

import numpy as np
import pandas as pd

from lob_engine.execution.base import ExecutionAlgorithm, allocate_integer_quantity, schedule_frame, time_grid


class VWAPExecutor(ExecutionAlgorithm):
    """Allocate child orders according to an expected volume curve."""

    name = "VWAP"

    def __init__(self, parent_order, volume_curve: list[float] | np.ndarray) -> None:
        super().__init__(parent_order)
        if len(volume_curve) == 0:
            raise ValueError("Volume curve cannot be empty.")
        self.volume_curve = np.asarray(volume_curve, dtype="float64")
        if np.any(self.volume_curve < 0) or self.volume_curve.sum() <= 0:
            raise ValueError("Volume curve must contain positive non-negative weights.")

    def build_schedule(self) -> pd.DataFrame:
        timestamps = time_grid(self.parent_order.start_time, self.parent_order.end_time, len(self.volume_curve))
        quantities = allocate_integer_quantity(self.parent_order.quantity, self.volume_curve)
        return schedule_frame(self.parent_order, self.name, timestamps, quantities)
