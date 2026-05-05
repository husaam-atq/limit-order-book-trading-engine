"""Child-order fill simulation using replay snapshots."""

from __future__ import annotations

import numpy as np
import pandas as pd

from lob_engine.core.orders import Side


def simulate_child_order_fills(
    schedule: pd.DataFrame, snapshots: pd.DataFrame, side: Side | str, impact_bps: float = 0.5
) -> pd.DataFrame:
    """Fill child orders against the latest available prior book snapshot."""

    if schedule.empty:
        return pd.DataFrame()
    if snapshots.empty:
        raise ValueError("Snapshots are required for fill simulation.")
    side = Side.from_value(side)
    sched = schedule.sort_values("timestamp").copy()
    snaps = snapshots.sort_values("timestamp").copy()
    merged = pd.merge_asof(sched, snaps, on="timestamp", direction="backward")
    if merged["mid_price"].isna().all():
        raise ValueError("No valid midpoint was available before scheduled orders.")
    merged["mid_price"] = merged["mid_price"].ffill().bfill()
    merged["spread"] = merged["spread"].fillna(0.02)
    if side is Side.BUY:
        base_price = merged["best_ask"].fillna(merged["mid_price"] + merged["spread"] / 2)
        impact = merged["mid_price"] * impact_bps / 10_000
        merged["fill_price"] = base_price + impact
    else:
        base_price = merged["best_bid"].fillna(merged["mid_price"] - merged["spread"] / 2)
        impact = merged["mid_price"] * impact_bps / 10_000
        merged["fill_price"] = np.maximum(base_price - impact, 0.01)
    merged["filled_quantity"] = merged["quantity"]
    return merged[
        [
            "algorithm",
            "parent_order_id",
            "child_order_id",
            "timestamp",
            "side",
            "quantity",
            "filled_quantity",
            "fill_price",
            "mid_price",
            "spread",
        ]
    ]
