"""Optimised matching engine used by benchmark and parity workflows."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from lob_engine.core.fast_order_book import (
    BUY,
    CANCELLED,
    FILLED,
    LIMIT,
    MARKET,
    MODIFY,
    PARTIALLY_FILLED,
    REJECTED,
    FastOrder,
    FastOrderBook,
)


@dataclass(frozen=True, slots=True)
class FastTrade:
    """Lightweight trade record from the optimised engine."""

    trade_number: int
    timestamp: float
    aggressor_order_id: str
    passive_order_id: str
    side: int
    price_ticks: int
    quantity: int
    aggressor_remaining: int
    passive_remaining: int

    def to_dict(self, tick_size: float = 0.01) -> dict[str, object]:
        """Return a reference-compatible trade dictionary."""

        side = "buy" if self.side == BUY else "sell"
        return {
            "trade_id": f"T{self.trade_number:08d}",
            "timestamp": self.timestamp,
            "aggressor_order_id": self.aggressor_order_id,
            "passive_order_id": self.passive_order_id,
            "side": side,
            "price": self.price_ticks * tick_size,
            "quantity": self.quantity,
            "maker_order_id": self.passive_order_id,
            "taker_order_id": self.aggressor_order_id,
            "aggressor_remaining": self.aggressor_remaining,
            "passive_remaining": self.passive_remaining,
        }


@dataclass(slots=True)
class FastOrderResult:
    """Compact request result from the optimised matching engine."""

    accepted: bool
    status: int
    filled_quantity: int
    remaining_quantity: int
    trade_count: int
    message: str = ""


class FastMatchingEngine:
    """Matching engine tuned for replay benchmarks while preserving priority rules."""

    def __init__(self, tick_size: float = 0.01, record_trades: bool = True) -> None:
        self.book = FastOrderBook(tick_size=tick_size)
        self.tick_size = tick_size
        self.record_trades = record_trades
        self.trades: list[FastTrade] = []
        self.rejections: list[dict[str, object]] = []
        self.trade_count = 0

    def reset(self) -> None:
        """Clear book and recorded engine state."""

        self.book.clear()
        self.trades.clear()
        self.rejections.clear()
        self.trade_count = 0

    def process_limit(
        self, order_id: str, side: int, quantity: int, price_ticks: int, timestamp: float
    ) -> FastOrderResult:
        """Process a limit order."""

        if order_id in self.book.order_lookup:
            self.rejections.append({"timestamp": timestamp, "order_id": order_id, "reason": "duplicate order id"})
            return FastOrderResult(False, REJECTED, 0, quantity, 0, "duplicate order id")
        order = FastOrder(order_id, side, quantity, quantity, price_ticks, timestamp)
        start_trades = self.trade_count
        self._match(order, LIMIT)
        if order.remaining > 0:
            self.book.add_order(order)
        status = FILLED if order.remaining == 0 else PARTIALLY_FILLED if order.remaining < quantity else order.status
        order.status = status
        return FastOrderResult(
            True, status, quantity - order.remaining, order.remaining, self.trade_count - start_trades
        )

    def process_market(self, order_id: str, side: int, quantity: int, timestamp: float) -> FastOrderResult:
        """Process a market order."""

        if order_id in self.book.order_lookup:
            self.rejections.append({"timestamp": timestamp, "order_id": order_id, "reason": "duplicate order id"})
            return FastOrderResult(False, REJECTED, 0, quantity, 0, "duplicate order id")
        order = FastOrder(order_id, side, quantity, quantity, 0, timestamp)
        start_trades = self.trade_count
        self._match(order, MARKET)
        status = FILLED if order.remaining == 0 else CANCELLED
        order.status = status
        order.active = False
        return FastOrderResult(
            True, status, quantity - order.remaining, order.remaining, self.trade_count - start_trades
        )

    def process_cancel(self, order_id: str, target_order_id: str, timestamp: float) -> FastOrderResult:
        """Cancel a resting order."""

        removed, order = self.book.cancel_order(target_order_id)
        if not removed:
            self.rejections.append({"timestamp": timestamp, "order_id": order_id, "reason": "cancel target not found"})
            return FastOrderResult(False, REJECTED, 0, 0, 0, "cancel target not found")
        return FastOrderResult(True, order.status, order.filled_quantity, order.remaining, 0)

    def process_modify(
        self, order_id: str, target_order_id: str, quantity: int, price_ticks: int, timestamp: float
    ) -> FastOrderResult:
        """Cancel and replace a resting order, losing queue priority."""

        existing = self.book.order_lookup.get(target_order_id)
        if existing is None:
            self.rejections.append({"timestamp": timestamp, "order_id": order_id, "reason": "modify target not found"})
            return FastOrderResult(False, REJECTED, 0, 0, 0, "modify target not found")
        side = existing.side
        self.book.cancel_order(target_order_id)
        return self.process_limit(target_order_id, side, quantity, price_ticks, timestamp)

    def process_event(
        self,
        event_type: int,
        order_id: str,
        side: int,
        quantity: int,
        price_ticks: int,
        timestamp: float,
        target_order_id: str,
    ) -> FastOrderResult:
        """Process an integer-coded event."""

        if event_type == LIMIT:
            return self.process_limit(order_id, side, quantity, price_ticks, timestamp)
        if event_type == MARKET:
            return self.process_market(order_id, side, quantity, timestamp)
        if event_type == MODIFY:
            return self.process_modify(order_id, target_order_id, quantity, price_ticks, timestamp)
        return self.process_cancel(order_id, target_order_id, timestamp)

    def trades_frame(self) -> pd.DataFrame:
        """Return recorded trades as a reference-compatible DataFrame."""

        return pd.DataFrame([trade.to_dict(self.tick_size) for trade in self.trades])

    def _match(self, incoming: FastOrder, order_type: int) -> None:
        while incoming.remaining > 0:
            if incoming.side == BUY:
                best_price = self.book.best_ask_ticks()
                if best_price is None:
                    return
                if order_type == LIMIT and incoming.price_ticks < best_price:
                    return
                opposite = self.book.asks
                qty_map = self.book.ask_qty
            else:
                best_price = self.book.best_bid_ticks()
                if best_price is None:
                    return
                if order_type == LIMIT and incoming.price_ticks > best_price:
                    return
                opposite = self.book.bids
                qty_map = self.book.bid_qty

            level = opposite.get(best_price)
            if not level:
                qty_map.pop(best_price, None)
                continue

            while level and (not level[0].active or level[0].remaining <= 0):
                level.popleft()
            if not level:
                opposite.pop(best_price, None)
                qty_map.pop(best_price, None)
                continue

            resting = level[0]
            fill_qty = incoming.remaining if incoming.remaining < resting.remaining else resting.remaining
            incoming.remaining -= fill_qty
            resting.remaining -= fill_qty
            qty_left_at_level = qty_map.get(best_price, 0) - fill_qty
            if qty_left_at_level > 0:
                qty_map[best_price] = qty_left_at_level
            else:
                qty_map.pop(best_price, None)

            incoming.status = FILLED if incoming.remaining == 0 else PARTIALLY_FILLED
            resting.status = FILLED if resting.remaining == 0 else PARTIALLY_FILLED
            self.trade_count += 1
            if self.record_trades:
                self.trades.append(
                    FastTrade(
                        self.trade_count,
                        incoming.timestamp,
                        incoming.order_id,
                        resting.order_id,
                        incoming.side,
                        best_price,
                        fill_qty,
                        incoming.remaining,
                        resting.remaining,
                    )
                )

            if resting.remaining == 0:
                resting.active = False
                level.popleft()
                self.book.order_lookup.pop(resting.order_id, None)
            if not level and qty_map.get(best_price, 0) <= 0:
                opposite.pop(best_price, None)


def side_to_str(side: int) -> str:
    """Return display string for an integer-coded side."""

    return "buy" if side == BUY else "sell"
