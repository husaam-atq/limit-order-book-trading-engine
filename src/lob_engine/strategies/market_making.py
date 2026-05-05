"""Simple inventory-aware market making strategy."""

from __future__ import annotations

import pandas as pd

from lob_engine.core.order_book import LimitOrderBook
from lob_engine.core.orders import Order, OrderType, Side


class MarketMakingStrategy:
    """Quote small bid/ask orders around the midpoint."""

    name = "market_making"

    def __init__(self, order_size: int = 20, quote_width: float = 0.03, max_inventory: int = 200) -> None:
        self.order_size = order_size
        self.quote_width = quote_width
        self.max_inventory = max_inventory
        self._counter = 0

    def generate_orders(
        self, timestamp: float, book: LimitOrderBook, history: pd.DataFrame, position: int
    ) -> list[Order]:
        mid = book.mid_price()
        if mid is None:
            return []
        orders: list[Order] = []
        if position < self.max_inventory:
            self._counter += 1
            orders.append(
                Order(
                    order_id=f"MM-B-{self._counter:08d}",
                    side=Side.BUY,
                    order_type=OrderType.LIMIT,
                    quantity=self.order_size,
                    price=round(mid - self.quote_width / 2, 2),
                    timestamp=timestamp + 1e-6,
                    trader_id="strategy",
                )
            )
        if position > -self.max_inventory:
            self._counter += 1
            orders.append(
                Order(
                    order_id=f"MM-S-{self._counter:08d}",
                    side=Side.SELL,
                    order_type=OrderType.LIMIT,
                    quantity=self.order_size,
                    price=round(mid + self.quote_width / 2, 2),
                    timestamp=timestamp + 1e-6,
                    trader_id="strategy",
                )
            )
        return orders
