"""Short-horizon momentum demonstration strategy."""

from __future__ import annotations

import pandas as pd

from lob_engine.core.order_book import LimitOrderBook
from lob_engine.core.orders import Order, OrderType, Side


class MomentumStrategy:
    """Trade in the direction of recent midpoint moves."""

    name = "momentum"

    def __init__(
        self, lookback: int = 20, threshold_bps: float = 2.0, order_size: int = 10, max_inventory: int = 100
    ) -> None:
        self.lookback = lookback
        self.threshold_bps = threshold_bps
        self.order_size = order_size
        self.max_inventory = max_inventory
        self._counter = 0

    def generate_orders(
        self, timestamp: float, book: LimitOrderBook, history: pd.DataFrame, position: int
    ) -> list[Order]:
        mids = history["mid_price"].dropna().astype(float)
        if len(mids) <= self.lookback:
            return []
        current = mids.iloc[-1]
        previous = mids.iloc[-self.lookback]
        move_bps = (current - previous) / previous * 10_000
        side = None
        if move_bps > self.threshold_bps and position < self.max_inventory:
            side = Side.BUY
        elif move_bps < -self.threshold_bps and position > -self.max_inventory:
            side = Side.SELL
        if side is None:
            return []
        self._counter += 1
        return [
            Order(
                order_id=f"MOM-{self._counter:08d}",
                side=side,
                order_type=OrderType.MARKET,
                quantity=self.order_size,
                timestamp=timestamp + 1e-6,
                trader_id="strategy",
            )
        ]
