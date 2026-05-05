"""Market event models and conversion helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Optional

from lob_engine.core.orders import CancelRequest, ModifyRequest, Order, OrderType, Side


class EventType(str, Enum):
    """Supported market event types."""

    LIMIT = "limit"
    MARKET = "market"
    CANCEL = "cancel"
    MODIFY = "modify"

    @classmethod
    def from_value(cls, value: str | "EventType") -> "EventType":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError as exc:
            raise ValueError(f"Invalid event type {value!r}.") from exc


@dataclass(frozen=True)
class MarketEvent:
    """Serializable event consumed by market replay."""

    timestamp: float
    event_type: EventType | str
    order_id: str
    side: Optional[Side | str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    trader_id: Optional[str] = None
    target_order_id: Optional[str] = None
    symbol: str = "SYNTH"

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", EventType.from_value(self.event_type))
        if self.side is not None:
            object.__setattr__(self, "side", Side.from_value(self.side))
        if self.timestamp < 0:
            raise ValueError("Event timestamp cannot be negative.")
        if not self.order_id:
            raise ValueError("Event order ID is required.")

    def to_order(self) -> Order:
        """Convert a limit or market event into an executable order."""

        if self.event_type not in {EventType.LIMIT, EventType.MARKET}:
            raise ValueError("Only limit and market events can be converted to orders.")
        if self.side is None:
            raise ValueError("Executable events require side.")
        if self.quantity is None:
            raise ValueError("Executable events require quantity.")
        return Order(
            order_id=self.order_id,
            side=self.side,
            order_type=OrderType.LIMIT if self.event_type is EventType.LIMIT else OrderType.MARKET,
            quantity=int(self.quantity),
            price=self.price,
            timestamp=self.timestamp,
            trader_id=self.trader_id,
            symbol=self.symbol,
        )

    def to_cancel(self) -> CancelRequest:
        """Convert a cancel event into a cancel request."""

        if self.event_type is not EventType.CANCEL:
            raise ValueError("Only cancel events can be converted to cancel requests.")
        if not self.target_order_id:
            raise ValueError("Cancel events require target_order_id.")
        return CancelRequest(
            order_id=self.order_id,
            timestamp=self.timestamp,
            target_order_id=self.target_order_id,
            trader_id=self.trader_id,
            symbol=self.symbol,
        )

    def to_modify(self) -> ModifyRequest:
        """Convert a modify event into a cancel/replace request."""

        if self.event_type is not EventType.MODIFY:
            raise ValueError("Only modify events can be converted to modify requests.")
        if not self.target_order_id:
            raise ValueError("Modify events require target_order_id.")
        if self.quantity is None or self.price is None:
            raise ValueError("Modify events require new quantity and price.")
        return ModifyRequest(
            order_id=self.order_id,
            timestamp=self.timestamp,
            target_order_id=self.target_order_id,
            new_quantity=int(self.quantity),
            new_price=float(self.price),
            trader_id=self.trader_id,
            symbol=self.symbol,
        )

    def to_dict(self) -> dict[str, object]:
        """Return a CSV-friendly dictionary."""

        row = asdict(self)
        row["event_type"] = self.event_type.value
        row["side"] = None if self.side is None else self.side.value
        return row
