"""Historical-style market replay without lookahead."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd

from lob_engine.analytics.microstructure import book_metrics
from lob_engine.core.events import EventType, MarketEvent
from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.order_book import LimitOrderBook


@dataclass
class ReplayResult:
    """Outputs captured from a deterministic market replay."""

    snapshots: pd.DataFrame
    trades: pd.DataFrame
    rejections: pd.DataFrame
    final_book: LimitOrderBook
    processed_events: int


class MarketReplay:
    """Sequentially replay event data through a matching engine."""

    def __init__(self, engine: Optional[MatchingEngine] = None, snapshot_depth: int = 5) -> None:
        self.engine = engine or MatchingEngine()
        self.snapshot_depth = snapshot_depth

    def replay(self, events: pd.DataFrame | str | Path, reset: bool = True) -> ReplayResult:
        """Replay events from a DataFrame or CSV path."""

        if reset:
            self.engine.reset()
        frame = pd.read_csv(events) if isinstance(events, (str, Path)) else events.copy()
        if frame.empty:
            return ReplayResult(pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), self.engine.book, 0)
        frame = frame.sort_values("timestamp", kind="mergesort").reset_index(drop=True)

        snapshot_rows: list[dict[str, object]] = []
        trade_rows: list[dict[str, object]] = []
        rejection_rows: list[dict[str, object]] = []

        for event_index, row in frame.iterrows():
            try:
                event = self._row_to_event(row)
                result = self._process_event(event)
                for trade in result.trades or []:
                    trade_dict = trade.to_dict()
                    trade_dict["event_index"] = event_index
                    trade_rows.append(trade_dict)
                if not result.accepted:
                    rejection_rows.append(
                        {
                            "event_index": event_index,
                            "timestamp": event.timestamp,
                            "order_id": event.order_id,
                            "message": result.message,
                        }
                    )
            except Exception as exc:
                rejection_rows.append(
                    {
                        "event_index": event_index,
                        "timestamp": row.get("timestamp", None),
                        "order_id": row.get("order_id", None),
                        "message": str(exc),
                    }
                )

            metrics = book_metrics(self.engine.book, self.snapshot_depth)
            metrics.update(
                {
                    "event_index": event_index,
                    "timestamp": float(row["timestamp"]),
                    "event_type": row["event_type"],
                    "order_id": row["order_id"],
                    "trade_count": len(trade_rows),
                    "resting_orders": len(self.engine.book),
                }
            )
            snapshot_rows.append(metrics)

        snapshots = pd.DataFrame(snapshot_rows)
        trades = pd.DataFrame(trade_rows)
        rejections = pd.DataFrame(rejection_rows)
        return ReplayResult(snapshots, trades, rejections, self.engine.book, len(frame))

    def _process_event(self, event: MarketEvent):
        if event.event_type in {EventType.LIMIT, EventType.MARKET}:
            return self.engine.process_order(event.to_order())
        if event.event_type is EventType.CANCEL:
            return self.engine.process_cancel(event.to_cancel())
        if event.event_type is EventType.MODIFY:
            return self.engine.process_modify(event.to_modify())
        raise ValueError(f"Unsupported event type {event.event_type}.")

    def _row_to_event(self, row: pd.Series) -> MarketEvent:
        side = None if pd.isna(row.get("side")) else row.get("side")
        quantity = None if pd.isna(row.get("quantity")) else int(row.get("quantity"))
        price = None if pd.isna(row.get("price")) else float(row.get("price"))
        target_order_id = None if pd.isna(row.get("target_order_id")) else str(row.get("target_order_id"))
        trader_id = None if pd.isna(row.get("trader_id")) else str(row.get("trader_id"))
        return MarketEvent(
            timestamp=float(row["timestamp"]),
            event_type=str(row["event_type"]),
            order_id=str(row["order_id"]),
            side=side,
            quantity=quantity,
            price=price,
            trader_id=trader_id,
            target_order_id=target_order_id,
            symbol=str(row.get("symbol", "SYNTH")),
        )
