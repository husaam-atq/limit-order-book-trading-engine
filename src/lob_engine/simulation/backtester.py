"""Event-driven strategy backtester built on the matching engine."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
import pandas as pd

from lob_engine.analytics.microstructure import book_metrics
from lob_engine.core.events import EventType, MarketEvent
from lob_engine.core.matching_engine import MatchingEngine, Trade
from lob_engine.core.orders import Order, Side


class Strategy(Protocol):
    """Protocol implemented by demo strategies."""

    name: str

    def generate_orders(self, timestamp: float, book, history: pd.DataFrame, position: int) -> list[Order]:
        """Return orders using only information available at the timestamp."""


@dataclass
class BacktestResult:
    """Backtest state path and summary metrics."""

    equity_curve: pd.DataFrame
    trades: pd.DataFrame
    orders: pd.DataFrame
    metrics: dict[str, float]


class EventDrivenBacktester:
    """Replay market events and submit strategy orders without lookahead."""

    def __init__(
        self,
        strategy: Strategy,
        starting_cash: float = 1_000_000.0,
        starting_inventory: int = 0,
        allow_short: bool = False,
        commission_bps: float = 0.1,
        snapshot_depth: int = 5,
    ) -> None:
        self.strategy = strategy
        self.starting_cash = starting_cash
        self.starting_inventory = starting_inventory
        self.allow_short = allow_short
        self.commission_bps = commission_bps
        self.snapshot_depth = snapshot_depth

    def run(self, events: pd.DataFrame | str | Path) -> BacktestResult:
        """Run a deterministic event-driven backtest."""

        frame = pd.read_csv(events) if isinstance(events, (str, Path)) else events.copy()
        frame = frame.sort_values("timestamp", kind="mergesort").reset_index(drop=True)
        engine = MatchingEngine()
        cash = float(self.starting_cash)
        inventory = int(self.starting_inventory)
        strategy_order_ids: set[str] = set()
        history_rows: list[dict[str, object]] = []
        strategy_trade_rows: list[dict[str, object]] = []
        order_rows: list[dict[str, object]] = []
        last_mid = np.nan

        for event_index, row in frame.iterrows():
            event = self._row_to_event(row)
            market_result = self._process_event(engine, event)
            cash, inventory = self._apply_strategy_fills(
                market_result.trades or [], strategy_order_ids, cash, inventory
            )

            metrics = book_metrics(engine.book, self.snapshot_depth)
            metrics.update({"timestamp": event.timestamp, "event_index": event_index})
            history = pd.DataFrame(history_rows + [metrics])
            if metrics["mid_price"] is not None:
                last_mid = float(metrics["mid_price"])

            for order in self.strategy.generate_orders(event.timestamp, engine.book, history, inventory):
                adjusted = self._risk_adjust(order, inventory, cash, last_mid)
                if adjusted is None:
                    continue
                strategy_order_ids.add(adjusted.order_id)
                order_rows.append(
                    {
                        "timestamp": adjusted.timestamp,
                        "order_id": adjusted.order_id,
                        "side": adjusted.side.value,
                        "order_type": adjusted.order_type.value,
                        "quantity": adjusted.quantity,
                        "price": adjusted.price,
                    }
                )
                result = engine.process_order(adjusted)
                cash, inventory = self._apply_strategy_fills(result.trades or [], strategy_order_ids, cash, inventory)
                for trade in result.trades or []:
                    if trade.aggressor_order_id in strategy_order_ids or trade.passive_order_id in strategy_order_ids:
                        strategy_trade_rows.append(trade.to_dict())

            mark = float(last_mid) if not np.isnan(last_mid) else 0.0
            equity = cash + inventory * mark
            metrics.update(
                {
                    "cash": cash,
                    "inventory": inventory,
                    "mark_price": mark,
                    "equity": equity,
                    "strategy_trades": len(strategy_trade_rows),
                }
            )
            history_rows.append(metrics)

        equity_curve = pd.DataFrame(history_rows)
        trades = pd.DataFrame(strategy_trade_rows)
        orders = pd.DataFrame(order_rows)
        metrics = self._summary_metrics(equity_curve, trades, orders)
        return BacktestResult(equity_curve=equity_curve, trades=trades, orders=orders, metrics=metrics)

    def _process_event(self, engine: MatchingEngine, event: MarketEvent):
        if event.event_type in {EventType.LIMIT, EventType.MARKET}:
            return engine.process_order(event.to_order())
        if event.event_type is EventType.CANCEL:
            return engine.process_cancel(event.to_cancel())
        if event.event_type is EventType.MODIFY:
            return engine.process_modify(event.to_modify())
        raise ValueError(f"Unsupported event type {event.event_type}.")

    def _apply_strategy_fills(
        self, trades: list[Trade], strategy_order_ids: set[str], cash: float, inventory: int
    ) -> tuple[float, int]:
        for trade in trades:
            is_aggressor = trade.aggressor_order_id in strategy_order_ids
            is_passive = trade.passive_order_id in strategy_order_ids
            if not is_aggressor and not is_passive:
                continue
            if is_aggressor:
                strategy_side = trade.side
            else:
                strategy_side = Side.SELL if trade.side is Side.BUY else Side.BUY
            notional = trade.price * trade.quantity
            commission = notional * self.commission_bps / 10_000
            if strategy_side is Side.BUY:
                inventory += trade.quantity
                cash -= notional + commission
            else:
                inventory -= trade.quantity
                cash += notional - commission
        return cash, inventory

    def _risk_adjust(self, order: Order, inventory: int, cash: float, mark_price: float) -> Order | None:
        if order.side is Side.SELL and not self.allow_short and order.quantity > inventory:
            if inventory <= 0:
                return None
            order = Order(
                order_id=order.order_id,
                side=order.side,
                order_type=order.order_type,
                quantity=inventory,
                price=order.price,
                timestamp=order.timestamp,
                trader_id=order.trader_id,
                symbol=order.symbol,
            )
        if order.side is Side.BUY and mark_price > 0:
            max_affordable = int(cash // mark_price)
            if max_affordable <= 0:
                return None
            if order.quantity > max_affordable:
                order = Order(
                    order_id=order.order_id,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=max_affordable,
                    price=order.price,
                    timestamp=order.timestamp,
                    trader_id=order.trader_id,
                    symbol=order.symbol,
                )
        return order

    def _summary_metrics(
        self, equity_curve: pd.DataFrame, trades: pd.DataFrame, orders: pd.DataFrame
    ) -> dict[str, float]:
        if equity_curve.empty:
            return {}
        equity = equity_curve["equity"].astype(float)
        running_max = equity.cummax()
        drawdown = (equity - running_max) / running_max.replace(0, np.nan)
        turnover = float(trades["price"].mul(trades["quantity"]).sum()) if not trades.empty else 0.0
        if len(orders) and not trades.empty:
            submitted_ids = set(orders["order_id"])
            filled_ids = (set(trades["aggressor_order_id"]) | set(trades["passive_order_id"])) & submitted_ids
            fill_rate = float(len(filled_ids) / len(orders))
        else:
            fill_rate = 0.0
        return {
            "ending_equity": float(equity.iloc[-1]),
            "total_pnl": float(
                equity.iloc[-1] - self.starting_cash - self.starting_inventory * equity_curve["mark_price"].iloc[0]
            ),
            "max_drawdown": float(drawdown.min()) if not drawdown.empty else 0.0,
            "ending_inventory": float(equity_curve["inventory"].iloc[-1]),
            "turnover": turnover,
            "fill_rate": fill_rate,
            "orders_submitted": float(len(orders)),
            "trades": float(len(trades)),
        }

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
