"""Optimised limit order book primitives for benchmark-focused replay."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from heapq import heappop, heappush

BUY = 1
SELL = -1

LIMIT = 1
MARKET = 2
CANCEL = 3
MODIFY = 4

NEW = 1
PARTIALLY_FILLED = 2
FILLED = 3
CANCELLED = 4
REJECTED = 5


@dataclass(slots=True)
class FastOrder:
    """Lightweight live order used by the optimised matching engine."""

    order_id: str
    side: int
    quantity: int
    remaining: int
    price_ticks: int
    timestamp: float
    status: int = NEW
    active: bool = True

    @property
    def filled_quantity(self) -> int:
        return self.quantity - self.remaining


@dataclass(frozen=True, slots=True)
class FastPriceLevel:
    """Price-level snapshot from the optimised order book."""

    side: int
    price_ticks: int
    quantity: int
    order_count: int


class FastOrderBook:
    """Heap-backed price-time priority book with lazy cancellation cleanup."""

    def __init__(self, tick_size: float = 0.01) -> None:
        self.tick_size = tick_size
        self.bids: dict[int, deque[FastOrder]] = {}
        self.asks: dict[int, deque[FastOrder]] = {}
        self.bid_qty: dict[int, int] = {}
        self.ask_qty: dict[int, int] = {}
        self.bid_heap: list[int] = []
        self.ask_heap: list[int] = []
        self.order_lookup: dict[str, FastOrder] = {}

    def __len__(self) -> int:
        return len(self.order_lookup)

    def clear(self) -> None:
        """Remove all live and queued book state."""

        self.bids.clear()
        self.asks.clear()
        self.bid_qty.clear()
        self.ask_qty.clear()
        self.bid_heap.clear()
        self.ask_heap.clear()
        self.order_lookup.clear()

    def add_order(self, order: FastOrder) -> bool:
        """Rest a live limit order and return whether it was accepted."""

        if order.order_id in self.order_lookup or order.remaining <= 0:
            return False
        if order.side == BUY:
            book = self.bids
            qty_map = self.bid_qty
            heap = self.bid_heap
            heap_price = -order.price_ticks
        else:
            book = self.asks
            qty_map = self.ask_qty
            heap = self.ask_heap
            heap_price = order.price_ticks
        was_empty = qty_map.get(order.price_ticks, 0) <= 0
        if order.price_ticks not in book:
            book[order.price_ticks] = deque()
        if was_empty:
            heappush(heap, heap_price)
        book[order.price_ticks].append(order)
        qty_map[order.price_ticks] = qty_map.get(order.price_ticks, 0) + order.remaining
        self.order_lookup[order.order_id] = order
        return True

    def cancel_order(self, order_id: str) -> tuple[bool, FastOrder | None]:
        """Cancel a live order in O(1), leaving queue cleanup to the next match."""

        order = self.order_lookup.pop(order_id, None)
        if order is None or not order.active or order.remaining <= 0:
            return False, order
        qty_map = self.bid_qty if order.side == BUY else self.ask_qty
        remaining = order.remaining
        current_qty = qty_map.get(order.price_ticks, 0) - remaining
        if current_qty > 0:
            qty_map[order.price_ticks] = current_qty
        else:
            qty_map.pop(order.price_ticks, None)
        order.remaining = 0
        order.status = CANCELLED
        order.active = False
        return True, order

    def best_bid_ticks(self) -> int | None:
        """Return best bid in integer ticks."""

        return self._best_ticks(BUY)

    def best_ask_ticks(self) -> int | None:
        """Return best ask in integer ticks."""

        return self._best_ticks(SELL)

    def best_bid(self) -> float | None:
        best = self.best_bid_ticks()
        return None if best is None else best * self.tick_size

    def best_ask(self) -> float | None:
        best = self.best_ask_ticks()
        return None if best is None else best * self.tick_size

    def mid_price(self) -> float | None:
        bid = self.best_bid_ticks()
        ask = self.best_ask_ticks()
        if bid is None or ask is None:
            return None
        return (bid + ask) * self.tick_size / 2.0

    def spread(self) -> float | None:
        bid = self.best_bid_ticks()
        ask = self.best_ask_ticks()
        if bid is None or ask is None:
            return None
        return (ask - bid) * self.tick_size

    def depth_at_ticks(self, side: int, price_ticks: int | None) -> int:
        """Return aggregate visible quantity at one price."""

        if price_ticks is None:
            return 0
        return (self.bid_qty if side == BUY else self.ask_qty).get(price_ticks, 0)

    def total_depth(self, side: int, levels: int | None = None) -> int:
        """Return aggregate visible depth over the top levels."""

        return sum(level.quantity for level in self.depth_levels(side, levels))

    def depth_levels(self, side: int, levels: int | None = None) -> list[FastPriceLevel]:
        """Return ordered visible price levels."""

        qty_map = self.bid_qty if side == BUY else self.ask_qty
        book = self.bids if side == BUY else self.asks
        prices = sorted(qty_map, reverse=side == BUY)
        if levels is not None:
            prices = prices[:levels]
        output = []
        for price_ticks in prices:
            queue = book.get(price_ticks)
            if not queue:
                continue
            self._clean_level_front(side, price_ticks)
            qty = qty_map.get(price_ticks, 0)
            if qty > 0:
                active_count = sum(1 for order in queue if order.active and order.remaining > 0)
                output.append(FastPriceLevel(side, price_ticks, qty, active_count))
        return output

    def snapshot(self, depth: int = 5) -> dict[str, float | int | None]:
        """Return a compact top-of-book snapshot."""

        bid = self.best_bid_ticks()
        ask = self.best_ask_ticks()
        mid = None if bid is None or ask is None else (bid + ask) * self.tick_size / 2.0
        spread = None if bid is None or ask is None else (ask - bid) * self.tick_size
        bid_depth = self.total_depth(BUY, depth)
        ask_depth = self.total_depth(SELL, depth)
        total = bid_depth + ask_depth
        imbalance = 0.0 if total == 0 else (bid_depth - ask_depth) / total
        return {
            "best_bid": None if bid is None else bid * self.tick_size,
            "best_ask": None if ask is None else ask * self.tick_size,
            "mid_price": mid,
            "spread": spread,
            "bid_depth": bid_depth,
            "ask_depth": ask_depth,
            "imbalance": imbalance,
            "resting_orders": len(self.order_lookup),
        }

    def _best_ticks(self, side: int) -> int | None:
        heap = self.bid_heap if side == BUY else self.ask_heap
        qty_map = self.bid_qty if side == BUY else self.ask_qty
        while heap:
            price_ticks = -heap[0] if side == BUY else heap[0]
            if qty_map.get(price_ticks, 0) <= 0:
                heappop(heap)
                continue
            self._clean_level_front(side, price_ticks)
            if qty_map.get(price_ticks, 0) > 0:
                return price_ticks
            heappop(heap)
        return None

    def _clean_level_front(self, side: int, price_ticks: int) -> None:
        book = self.bids if side == BUY else self.asks
        queue = book.get(price_ticks)
        if queue is None:
            return
        while queue and (not queue[0].active or queue[0].remaining <= 0):
            queue.popleft()
        if not queue and (self.bid_qty if side == BUY else self.ask_qty).get(price_ticks, 0) <= 0:
            book.pop(price_ticks, None)
