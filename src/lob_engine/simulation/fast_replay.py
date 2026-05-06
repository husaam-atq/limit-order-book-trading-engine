"""Optimised replay loop for benchmark and parity workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from lob_engine.core.fast_matching_engine import FastMatchingEngine
from lob_engine.core.fast_order_book import BUY, CANCEL, LIMIT, MARKET, MODIFY, SELL


@dataclass(frozen=True, slots=True)
class FastEvent:
    """Integer-coded replay event."""

    timestamp: float
    event_type: int
    order_id: str
    side: int
    quantity: int
    price_ticks: int
    target_order_id: str


@dataclass
class FastReplayResult:
    """Outputs from the optimised replay loop."""

    snapshots: pd.DataFrame
    trades: pd.DataFrame
    rejections: pd.DataFrame
    final_book: object
    processed_events: int
    trade_count: int


def price_to_ticks(price: float | int | None, tick_size: float = 0.01) -> int:
    """Convert a price to integer ticks."""

    if price is None or pd.isna(price):
        return 0
    return int(round(float(price) / tick_size))


def ticks_to_price(price_ticks: int, tick_size: float = 0.01) -> float:
    """Convert integer ticks to a display price."""

    return price_ticks * tick_size


def prepare_fast_events(events: pd.DataFrame | str | Path, tick_size: float = 0.01) -> list[FastEvent]:
    """Pre-convert DataFrame/CSV events into lightweight integer-coded records."""

    frame = pd.read_csv(events) if isinstance(events, (str, Path)) else events
    if frame.empty:
        return []
    frame = frame.sort_values("timestamp", kind="mergesort")
    output: list[FastEvent] = []
    for row in frame.itertuples(index=False):
        event_type_value = row.event_type
        if event_type_value == "limit":
            event_type = LIMIT
        elif event_type_value == "market":
            event_type = MARKET
        elif event_type_value == "modify":
            event_type = MODIFY
        else:
            event_type = CANCEL

        side_value = row.side
        side = BUY if side_value == "buy" else SELL if side_value == "sell" else 0
        quantity = 0 if pd.isna(row.quantity) else int(row.quantity)
        price_ticks = price_to_ticks(row.price, tick_size)
        target = "" if pd.isna(row.target_order_id) else str(row.target_order_id)
        output.append(
            FastEvent(
                timestamp=float(row.timestamp),
                event_type=event_type,
                order_id=str(row.order_id),
                side=side,
                quantity=quantity,
                price_ticks=price_ticks,
                target_order_id=target,
            )
        )
    return output


class FastMarketReplay:
    """Replay prepared events through the optimised matching engine."""

    def __init__(self, tick_size: float = 0.01, snapshot_depth: int = 5, record_trades: bool = True) -> None:
        self.tick_size = tick_size
        self.snapshot_depth = snapshot_depth
        self.engine = FastMatchingEngine(tick_size=tick_size, record_trades=record_trades)

    def replay(
        self,
        events: list[FastEvent] | pd.DataFrame | str | Path,
        reset: bool = True,
        snapshots: bool = False,
        snapshot_interval: int = 1,
    ) -> FastReplayResult:
        """Replay events with optional lightweight snapshots."""

        if reset:
            self.engine.reset()
        prepared = prepare_fast_events(events, self.tick_size) if not isinstance(events, list) else events
        snapshot_rows: list[dict[str, object]] = []
        rejection_rows: list[dict[str, object]] = []
        for event_index, event in enumerate(prepared):
            result = self.engine.process_event(
                event.event_type,
                event.order_id,
                event.side,
                event.quantity,
                event.price_ticks,
                event.timestamp,
                event.target_order_id,
            )
            if not result.accepted:
                rejection_rows.append(
                    {
                        "event_index": event_index,
                        "timestamp": event.timestamp,
                        "order_id": event.order_id,
                        "message": result.message,
                    }
                )
            if snapshots and event_index % snapshot_interval == 0:
                row = self.engine.book.snapshot(self.snapshot_depth)
                row.update(
                    {
                        "event_index": event_index,
                        "timestamp": event.timestamp,
                        "trade_count": self.engine.trade_count,
                    }
                )
                snapshot_rows.append(row)

        trades = self.engine.trades_frame() if self.engine.record_trades else pd.DataFrame()
        return FastReplayResult(
            snapshots=pd.DataFrame(snapshot_rows),
            trades=trades,
            rejections=pd.DataFrame(rejection_rows),
            final_book=self.engine.book,
            processed_events=len(prepared),
            trade_count=self.engine.trade_count,
        )
