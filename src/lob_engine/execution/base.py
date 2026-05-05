"""Shared execution algorithm models and utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from lob_engine.analytics.slippage import benchmark_vwap, implementation_shortfall, slippage_bps, slippage_price
from lob_engine.analytics.transaction_costs import total_transaction_cost
from lob_engine.core.orders import Side


@dataclass(frozen=True)
class ParentOrder:
    """Large order to be split into executable child orders."""

    parent_order_id: str
    side: Side | str
    quantity: int
    start_time: float
    end_time: float
    arrival_price: float
    symbol: str = "SYNTH"

    def __post_init__(self) -> None:
        object.__setattr__(self, "side", Side.from_value(self.side))
        if not self.parent_order_id:
            raise ValueError("Parent order ID is required.")
        if self.quantity <= 0:
            raise ValueError("Parent quantity must be positive.")
        if self.end_time < self.start_time:
            raise ValueError("End time must be at or after start time.")
        if self.arrival_price <= 0:
            raise ValueError("Arrival price must be positive.")


@dataclass(frozen=True)
class ChildOrder:
    """Scheduled child order."""

    child_order_id: str
    parent_order_id: str
    timestamp: float
    side: Side
    quantity: int
    order_type: str = "market"
    limit_price: Optional[float] = None


@dataclass
class ExecutionResult:
    """Execution schedule, fills, and quality metrics."""

    algorithm: str
    parent_order: ParentOrder
    schedule: pd.DataFrame
    fills: pd.DataFrame = field(default_factory=pd.DataFrame)
    metrics: dict[str, float] = field(default_factory=dict)


class ExecutionAlgorithm:
    """Base class for deterministic execution schedules."""

    name = "base"

    def __init__(self, parent_order: ParentOrder) -> None:
        self.parent_order = parent_order

    def build_schedule(self) -> pd.DataFrame:
        raise NotImplementedError

    def execute_against_prices(
        self,
        prices: list[float] | np.ndarray,
        spreads: list[float] | np.ndarray | None = None,
        market_volumes: list[int] | np.ndarray | None = None,
    ) -> ExecutionResult:
        """Create a simple deterministic fill model for a schedule."""

        schedule = self.build_schedule()
        if schedule.empty:
            raise ValueError("Execution schedule is empty.")
        prices_arr = np.asarray(prices, dtype="float64")
        if len(prices_arr) < len(schedule):
            prices_arr = np.resize(prices_arr, len(schedule))
        spreads_arr = np.zeros(len(schedule)) + 0.02 if spreads is None else np.asarray(spreads, dtype="float64")
        if len(spreads_arr) < len(schedule):
            spreads_arr = np.resize(spreads_arr, len(schedule))

        signed_half_spread = 0.5 if self.parent_order.side is Side.BUY else -0.5
        fill_prices = prices_arr[: len(schedule)] + signed_half_spread * spreads_arr[: len(schedule)]
        fills = schedule.copy()
        fills["fill_price"] = fill_prices
        fills["filled_quantity"] = fills["quantity"]
        if market_volumes is None:
            fills["market_volume"] = fills["quantity"].clip(lower=1) / 0.1
        else:
            volumes = np.asarray(market_volumes, dtype="float64")
            fills["market_volume"] = np.resize(volumes, len(schedule))[: len(schedule)]
        metrics = summarize_fills(self.parent_order, fills)
        return ExecutionResult(self.name, self.parent_order, schedule, fills, metrics)


def time_grid(start_time: float, end_time: float, slices: int) -> np.ndarray:
    """Return deterministic child-order timestamps."""

    if slices <= 0:
        raise ValueError("Number of slices must be positive.")
    if slices == 1:
        return np.array([start_time], dtype="float64")
    return np.linspace(start_time, end_time, slices)


def allocate_integer_quantity(total_quantity: int, weights: list[float] | np.ndarray) -> list[int]:
    """Allocate an integer quantity exactly according to positive weights."""

    if total_quantity <= 0:
        raise ValueError("Total quantity must be positive.")
    weights_arr = np.asarray(weights, dtype="float64")
    if len(weights_arr) == 0:
        raise ValueError("At least one weight is required.")
    if np.any(weights_arr < 0):
        raise ValueError("Weights cannot be negative.")
    if weights_arr.sum() <= 0:
        raise ValueError("At least one weight must be positive.")

    raw = weights_arr / weights_arr.sum() * total_quantity
    base = np.floor(raw).astype(int)
    remainder = int(total_quantity - base.sum())
    if remainder > 0:
        order = np.argsort(-(raw - base))
        for idx in order[:remainder]:
            base[idx] += 1
    return base.astype(int).tolist()


def schedule_frame(parent: ParentOrder, algorithm: str, timestamps: np.ndarray, quantities: list[int]) -> pd.DataFrame:
    """Return a normalized child-order schedule DataFrame."""

    rows = []
    child_idx = 0
    for timestamp, quantity in zip(timestamps, quantities):
        if quantity <= 0:
            continue
        child_idx += 1
        rows.append(
            {
                "algorithm": algorithm,
                "parent_order_id": parent.parent_order_id,
                "child_order_id": f"{parent.parent_order_id}-{child_idx:04d}",
                "timestamp": float(timestamp),
                "side": parent.side.value,
                "quantity": int(quantity),
                "order_type": "market",
            }
        )
    return pd.DataFrame(rows)


def summarize_fills(parent: ParentOrder, fills: pd.DataFrame, benchmark_price: float | None = None) -> dict[str, float]:
    """Return execution quality metrics from child-order fills."""

    if fills.empty:
        return {
            "parent_quantity": float(parent.quantity),
            "filled_quantity": 0.0,
            "unfilled_quantity": float(parent.quantity),
            "fill_ratio": 0.0,
        }
    filled_qty = float(fills["filled_quantity"].sum())
    avg_price = benchmark_vwap(fills["fill_price"], fills["filled_quantity"])
    benchmark = float(benchmark_price if benchmark_price is not None else fills["fill_price"].mean())
    arrival = parent.arrival_price
    participation = (
        float(filled_qty / fills["market_volume"].sum())
        if "market_volume" in fills and fills["market_volume"].sum()
        else 0.0
    )
    duration = float(fills["timestamp"].max() - fills["timestamp"].min()) if len(fills) > 1 else 0.0
    spread = float(fills.get("spread", pd.Series([0.02])).mean())
    costs = total_transaction_cost(
        quantity=max(filled_qty, 1.0),
        price=avg_price,
        spread=spread,
        average_daily_volume=max(float(fills.get("market_volume", pd.Series([filled_qty * 10])).sum()), 1.0),
        volatility=0.02,
    )
    return {
        "parent_quantity": float(parent.quantity),
        "filled_quantity": filled_qty,
        "unfilled_quantity": float(max(parent.quantity - filled_qty, 0.0)),
        "average_fill_price": float(avg_price),
        "arrival_price": float(arrival),
        "benchmark_price": float(benchmark),
        "slippage_price": float(slippage_price(avg_price, benchmark, parent.side)),
        "slippage_bps": float(slippage_bps(avg_price, benchmark, parent.side)),
        "implementation_shortfall_bps": float(implementation_shortfall(avg_price, arrival, parent.side)),
        "participation_rate": participation,
        "execution_duration": duration,
        "fill_ratio": float(filled_qty / parent.quantity),
        "transaction_cost_bps": float(costs.total_cost_bps),
    }
