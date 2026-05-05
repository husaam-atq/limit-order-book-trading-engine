"""Mid-price mean-reversion demonstration strategy."""

from __future__ import annotations

import pandas as pd

from lob_engine.core.order_book import LimitOrderBook
from lob_engine.core.orders import Order, OrderType, Side


class MeanReversionStrategy:
    """Trade small market orders when mid price deviates from a rolling mean."""

    name = "mean_reversion"

    def __init__(
        self, window: int = 25, threshold_bps: float = 3.0, order_size: int = 10, max_inventory: int = 100
    ) -> None:
        self.window = window
        self.threshold_bps = threshold_bps
        self.order_size = order_size
        self.max_inventory = max_inventory
        self._counter = 0

    def generate_orders(
        self, timestamp: float, book: LimitOrderBook, history: pd.DataFrame, position: int
    ) -> list[Order]:
        if len(history) < self.window:
            return []
        mids = history["mid_price"].dropna().astype(float)
        if len(mids) < self.window:
            return []
        mid = mids.iloc[-1]
        rolling_mean = mids.iloc[-self.window :].mean()
        deviation_bps = (mid - rolling_mean) / rolling_mean * 10_000
        side = None
        if deviation_bps < -self.threshold_bps and position < self.max_inventory:
            side = Side.BUY
        elif deviation_bps > self.threshold_bps and position > -self.max_inventory:
            side = Side.SELL
        if side is None:
            return []
        self._counter += 1
        return [
            Order(
                order_id=f"MR-{self._counter:08d}",
                side=side,
                order_type=OrderType.MARKET,
                quantity=self.order_size,
                timestamp=timestamp + 1e-6,
                trader_id="strategy",
            )
        ]
