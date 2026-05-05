"""Deterministic price-time priority limit order book."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, Optional

import pandas as pd

from lob_engine.core.orders import Order, OrderStatus, OrderType, Side


@dataclass(frozen=True)
class PriceLevel:
    """Immutable snapshot of one price level."""

    side: Side
    price: float
    quantity: int
    order_count: int


class LimitOrderBook:
    """FIFO limit order book with price-time priority."""

    def __init__(self, symbol: str = "SYNTH") -> None:
        self.symbol = symbol
        self.bids: Dict[float, Deque[Order]] = {}
        self.asks: Dict[float, Deque[Order]] = {}
        self.order_lookup: Dict[str, Order] = {}

    def __len__(self) -> int:
        return len(self.order_lookup)

    def clear(self) -> None:
        """Remove all resting orders."""

        self.bids.clear()
        self.asks.clear()
        self.order_lookup.clear()

    def _book_for_side(self, side: Side) -> Dict[float, Deque[Order]]:
        return self.bids if side is Side.BUY else self.asks

    def _opposite_book(self, side: Side) -> Dict[float, Deque[Order]]:
        return self.asks if side is Side.BUY else self.bids

    def add_order(self, order: Order) -> None:
        """Add a live limit order to the book."""

        if order.order_type is not OrderType.LIMIT:
            raise ValueError("Only limit orders can rest in the order book.")
        if order.status not in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED}:
            raise ValueError("Only live orders can be added to the order book.")
        if order.remaining_quantity <= 0:
            raise ValueError("Order has no remaining quantity to add.")
        if order.order_id in self.order_lookup:
            raise ValueError(f"Duplicate order ID {order.order_id!r}.")

        book = self._book_for_side(order.side)
        book.setdefault(float(order.price), deque()).append(order)
        self.order_lookup[order.order_id] = order

    def cancel_order(self, order_id: str) -> tuple[bool, Optional[Order]]:
        """Cancel an existing resting order by ID."""

        order = self.order_lookup.get(order_id)
        if order is None:
            return False, None

        book = self._book_for_side(order.side)
        level = book.get(float(order.price))
        if level is None:
            self.order_lookup.pop(order_id, None)
            order.cancel()
            return False, order

        kept = deque(existing for existing in level if existing.order_id != order_id)
        if kept:
            book[float(order.price)] = kept
        else:
            book.pop(float(order.price), None)
        self.order_lookup.pop(order_id, None)
        order.cancel()
        return True, order

    def modify_order(
        self, order_id: str, new_quantity: int, new_price: float, timestamp: float
    ) -> tuple[bool, Optional[Order]]:
        """Cancel and replace a resting order, losing original queue priority."""

        existing = self.order_lookup.get(order_id)
        if existing is None:
            return False, None
        old_trader = existing.trader_id
        old_side = existing.side
        old_symbol = existing.symbol
        self.cancel_order(order_id)
        replacement = Order(
            order_id=order_id,
            side=old_side,
            order_type=OrderType.LIMIT,
            quantity=new_quantity,
            price=new_price,
            timestamp=timestamp,
            trader_id=old_trader,
            symbol=old_symbol,
        )
        self.add_order(replacement)
        return True, replacement

    def get_order(self, order_id: str) -> Optional[Order]:
        """Return a resting order by ID if present."""

        return self.order_lookup.get(order_id)

    def best_bid(self) -> Optional[float]:
        """Return the highest bid price."""

        return max(self.bids) if self.bids else None

    def best_ask(self) -> Optional[float]:
        """Return the lowest ask price."""

        return min(self.asks) if self.asks else None

    def best_bid_size(self) -> int:
        bid = self.best_bid()
        return self.depth_at_price(Side.BUY, bid) if bid is not None else 0

    def best_ask_size(self) -> int:
        ask = self.best_ask()
        return self.depth_at_price(Side.SELL, ask) if ask is not None else 0

    def mid_price(self) -> Optional[float]:
        """Return the best bid/ask midpoint if both sides are populated."""

        bid = self.best_bid()
        ask = self.best_ask()
        if bid is None or ask is None:
            return None
        return (bid + ask) / 2.0

    def spread(self) -> Optional[float]:
        """Return the quoted spread if both sides are populated."""

        bid = self.best_bid()
        ask = self.best_ask()
        if bid is None or ask is None:
            return None
        return ask - bid

    def depth_at_price(self, side: Side | str, price: Optional[float]) -> int:
        """Return visible quantity at a price level."""

        if price is None:
            return 0
        side = Side.from_value(side)
        level = self._book_for_side(side).get(float(price), deque())
        return int(sum(order.remaining_quantity for order in level))

    def order_count_at_price(self, side: Side | str, price: Optional[float]) -> int:
        """Return number of resting orders at a price level."""

        if price is None:
            return 0
        side = Side.from_value(side)
        return len(self._book_for_side(side).get(float(price), deque()))

    def total_depth(self, side: Side | str, levels: Optional[int] = None) -> int:
        """Return total visible quantity for one side."""

        return sum(level.quantity for level in self.depth_levels(side, levels=levels))

    def depth_levels(self, side: Side | str, levels: Optional[int] = None) -> list[PriceLevel]:
        """Return ordered price-level snapshots."""

        side = Side.from_value(side)
        book = self._book_for_side(side)
        reverse = side is Side.BUY
        prices = sorted(book.keys(), reverse=reverse)
        if levels is not None:
            prices = prices[:levels]
        snapshots: list[PriceLevel] = []
        for price in prices:
            queue = book[price]
            qty = int(sum(order.remaining_quantity for order in queue))
            if qty > 0:
                snapshots.append(PriceLevel(side=side, price=price, quantity=qty, order_count=len(queue)))
        return snapshots

    def top_n_levels(self, n: int = 5) -> pd.DataFrame:
        """Return a top-of-book ladder DataFrame."""

        rows = []
        for level in self.depth_levels(Side.BUY, n):
            rows.append({"side": "bid", "price": level.price, "quantity": level.quantity, "orders": level.order_count})
        for level in self.depth_levels(Side.SELL, n):
            rows.append({"side": "ask", "price": level.price, "quantity": level.quantity, "orders": level.order_count})
        return pd.DataFrame(rows, columns=["side", "price", "quantity", "orders"])

    def full_book_snapshot(self) -> pd.DataFrame:
        """Return every visible price level in the book."""

        return self.top_n_levels(n=max(len(self.bids), len(self.asks), 1))

    def snapshot(self, depth: int = 5) -> dict[str, object]:
        """Return a compact serialisable book snapshot."""

        return {
            "symbol": self.symbol,
            "best_bid": self.best_bid(),
            "best_ask": self.best_ask(),
            "mid_price": self.mid_price(),
            "spread": self.spread(),
            "bid_depth": self.total_depth(Side.BUY, depth),
            "ask_depth": self.total_depth(Side.SELL, depth),
            "order_count": len(self.order_lookup),
            "bids": [level.__dict__ for level in self.depth_levels(Side.BUY, depth)],
            "asks": [level.__dict__ for level in self.depth_levels(Side.SELL, depth)],
        }

    def iter_orders(self, side: Optional[Side | str] = None) -> Iterable[Order]:
        """Iterate over resting orders in book priority order."""

        if side is not None:
            side = Side.from_value(side)
            books = [self._book_for_side(side)]
            sides = [side]
        else:
            books = [self.bids, self.asks]
            sides = [Side.BUY, Side.SELL]
        for current_side, book in zip(sides, books):
            reverse = current_side is Side.BUY
            for price in sorted(book.keys(), reverse=reverse):
                yield from book[price]
