"""Order and request models for the limit order book."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Side(str, Enum):
    """Supported order sides."""

    BUY = "buy"
    SELL = "sell"

    @classmethod
    def from_value(cls, value: str | "Side") -> "Side":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError as exc:
            raise ValueError(f"Invalid side {value!r}; expected 'buy' or 'sell'.") from exc

    @property
    def opposite(self) -> "Side":
        return Side.SELL if self is Side.BUY else Side.BUY


class OrderType(str, Enum):
    """Supported executable order types."""

    MARKET = "market"
    LIMIT = "limit"

    @classmethod
    def from_value(cls, value: str | "OrderType") -> "OrderType":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError as exc:
            raise ValueError(f"Invalid order type {value!r}; expected 'market' or 'limit'.") from exc


class OrderStatus(str, Enum):
    """Order lifecycle states."""

    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Executable order tracked by the matching engine."""

    order_id: str
    side: Side | str
    order_type: OrderType | str
    quantity: int
    price: Optional[float] = None
    timestamp: float = 0.0
    trader_id: Optional[str] = None
    symbol: str = "SYNTH"
    status: OrderStatus = OrderStatus.NEW
    remaining_quantity: int = field(init=False)
    filled_quantity: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.side = Side.from_value(self.side)
        self.order_type = OrderType.from_value(self.order_type)
        if not self.order_id:
            raise ValueError("Order ID is required.")
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive.")
        if self.timestamp < 0:
            raise ValueError("Order timestamp cannot be negative.")
        if self.order_type is OrderType.LIMIT:
            if self.price is None:
                raise ValueError("Limit orders require a price.")
            if self.price <= 0:
                raise ValueError("Limit order price must be positive.")
            self.price = float(self.price)
        elif self.order_type is OrderType.MARKET:
            if self.price is not None and self.price < 0:
                raise ValueError("Market order price cannot be negative.")
            self.price = None
        self.remaining_quantity = int(self.quantity)

    @property
    def is_active(self) -> bool:
        """Return whether the order still has live quantity."""

        return self.status in {OrderStatus.NEW, OrderStatus.PARTIALLY_FILLED} and self.remaining_quantity > 0

    @property
    def is_buy(self) -> bool:
        return self.side is Side.BUY

    @property
    def is_sell(self) -> bool:
        return self.side is Side.SELL

    def record_fill(self, quantity: int) -> None:
        """Apply a fill to the order and update lifecycle state."""

        if quantity <= 0:
            raise ValueError("Fill quantity must be positive.")
        if quantity > self.remaining_quantity:
            raise ValueError("Fill quantity cannot exceed remaining quantity.")
        self.remaining_quantity -= int(quantity)
        self.filled_quantity += int(quantity)
        self.status = OrderStatus.FILLED if self.remaining_quantity == 0 else OrderStatus.PARTIALLY_FILLED

    def cancel(self) -> None:
        """Cancel any remaining live quantity."""

        if self.status is not OrderStatus.FILLED:
            self.status = OrderStatus.CANCELLED

    def reject(self) -> None:
        """Mark the order as rejected."""

        self.status = OrderStatus.REJECTED


@dataclass(frozen=True)
class CancelRequest:
    """Request to cancel a live resting order."""

    order_id: str
    timestamp: float
    target_order_id: str
    trader_id: Optional[str] = None
    symbol: str = "SYNTH"

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("Cancel request ID is required.")
        if not self.target_order_id:
            raise ValueError("Cancel target order ID is required.")
        if self.timestamp < 0:
            raise ValueError("Cancel timestamp cannot be negative.")


@dataclass(frozen=True)
class ModifyRequest:
    """Cancel/replace request that loses queue priority."""

    order_id: str
    timestamp: float
    target_order_id: str
    new_quantity: int
    new_price: float
    trader_id: Optional[str] = None
    symbol: str = "SYNTH"

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("Modify request ID is required.")
        if not self.target_order_id:
            raise ValueError("Modify target order ID is required.")
        if self.timestamp < 0:
            raise ValueError("Modify timestamp cannot be negative.")
        if self.new_quantity <= 0:
            raise ValueError("Modified quantity must be positive.")
        if self.new_price <= 0:
            raise ValueError("Modified price must be positive.")
