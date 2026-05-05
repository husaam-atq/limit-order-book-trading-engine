"""Price-time priority matching engine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

import pandas as pd

from lob_engine.core.order_book import LimitOrderBook
from lob_engine.core.orders import CancelRequest, ModifyRequest, Order, OrderStatus, OrderType, Side


@dataclass(frozen=True)
class Trade:
    """Execution record produced by the matching engine."""

    trade_id: str
    timestamp: float
    aggressor_order_id: str
    passive_order_id: str
    side: Side
    price: float
    quantity: int
    maker_order_id: str
    taker_order_id: str
    aggressor_remaining: int
    passive_remaining: int

    def to_dict(self) -> dict[str, object]:
        row = asdict(self)
        row["side"] = self.side.value
        return row


@dataclass
class OrderResult:
    """Result returned for every engine request."""

    accepted: bool
    message: str
    order: Optional[Order] = None
    trades: list[Trade] | None = None

    @property
    def trade_count(self) -> int:
        return len(self.trades or [])


class MatchingEngine:
    """Processes market, limit, cancel, and cancel/replace requests."""

    def __init__(self, book: Optional[LimitOrderBook] = None) -> None:
        self.book = book or LimitOrderBook()
        self.trades: list[Trade] = []
        self.rejections: list[dict[str, object]] = []
        self._trade_counter = 0

    def reset(self) -> None:
        """Clear order book and recorded trades."""

        self.book.clear()
        self.trades.clear()
        self.rejections.clear()
        self._trade_counter = 0

    def process_order(self, order: Order) -> OrderResult:
        """Process an executable order through the matching engine."""

        if order.order_id in self.book.order_lookup:
            order.reject()
            message = f"Duplicate order ID {order.order_id!r}."
            self.rejections.append({"timestamp": order.timestamp, "order_id": order.order_id, "reason": message})
            return OrderResult(False, message, order=order, trades=[])

        trades = self._match(order)
        if (
            order.order_type is OrderType.LIMIT
            and order.remaining_quantity > 0
            and order.status is not OrderStatus.REJECTED
        ):
            self.book.add_order(order)
            message = "Limit order rested." if not trades else "Limit order partially filled and rested."
        elif order.order_type is OrderType.MARKET and order.remaining_quantity > 0:
            order.cancel()
            message = (
                "Market order fully matched." if order.remaining_quantity == 0 else "Market order remainder cancelled."
            )
        else:
            message = "Order fully matched." if trades else "Order accepted."

        return OrderResult(True, message, order=order, trades=trades)

    def process_cancel(self, cancel: CancelRequest) -> OrderResult:
        """Cancel a resting order."""

        removed, order = self.book.cancel_order(cancel.target_order_id)
        if not removed:
            message = f"Cancel rejected: order {cancel.target_order_id!r} not found."
            self.rejections.append({"timestamp": cancel.timestamp, "order_id": cancel.order_id, "reason": message})
            return OrderResult(False, message, order=order, trades=[])
        return OrderResult(True, "Cancel accepted.", order=order, trades=[])

    def process_modify(self, modify: ModifyRequest) -> OrderResult:
        """Cancel and replace an existing order, then process the replacement."""

        existing = self.book.get_order(modify.target_order_id)
        if existing is None:
            message = f"Modify rejected: order {modify.target_order_id!r} not found."
            self.rejections.append({"timestamp": modify.timestamp, "order_id": modify.order_id, "reason": message})
            return OrderResult(False, message, order=None, trades=[])

        self.book.cancel_order(modify.target_order_id)
        replacement = Order(
            order_id=modify.target_order_id,
            side=existing.side,
            order_type=OrderType.LIMIT,
            quantity=modify.new_quantity,
            price=modify.new_price,
            timestamp=modify.timestamp,
            trader_id=existing.trader_id,
            symbol=existing.symbol,
        )
        return self.process_order(replacement)

    def trades_frame(self) -> pd.DataFrame:
        """Return all trades as a DataFrame."""

        return pd.DataFrame([trade.to_dict() for trade in self.trades])

    def _match(self, incoming: Order) -> list[Trade]:
        trades: list[Trade] = []
        while incoming.remaining_quantity > 0:
            best_price = self.book.best_ask() if incoming.side is Side.BUY else self.book.best_bid()
            if best_price is None:
                break
            if incoming.order_type is OrderType.LIMIT and not self._crosses(incoming, best_price):
                break

            opposite_book = self.book.asks if incoming.side is Side.BUY else self.book.bids
            level = opposite_book.get(float(best_price))
            if not level:
                opposite_book.pop(float(best_price), None)
                continue

            resting = level[0]
            fill_qty = min(incoming.remaining_quantity, resting.remaining_quantity)
            incoming.record_fill(fill_qty)
            resting.record_fill(fill_qty)
            trade = self._record_trade(incoming, resting, float(best_price), fill_qty)
            trades.append(trade)

            if resting.remaining_quantity == 0:
                level.popleft()
                self.book.order_lookup.pop(resting.order_id, None)
            if not level:
                opposite_book.pop(float(best_price), None)

        return trades

    def _crosses(self, incoming: Order, best_opposite_price: float) -> bool:
        if incoming.order_type is OrderType.MARKET:
            return True
        if incoming.price is None:
            return False
        if incoming.side is Side.BUY:
            return incoming.price >= best_opposite_price
        return incoming.price <= best_opposite_price

    def _record_trade(self, incoming: Order, resting: Order, price: float, quantity: int) -> Trade:
        self._trade_counter += 1
        trade = Trade(
            trade_id=f"T{self._trade_counter:08d}",
            timestamp=incoming.timestamp,
            aggressor_order_id=incoming.order_id,
            passive_order_id=resting.order_id,
            side=incoming.side,
            price=price,
            quantity=quantity,
            maker_order_id=resting.order_id,
            taker_order_id=incoming.order_id,
            aggressor_remaining=incoming.remaining_quantity,
            passive_remaining=resting.remaining_quantity,
        )
        self.trades.append(trade)
        return trade
