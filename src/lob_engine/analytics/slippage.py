"""Slippage and benchmark-price analytics."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from lob_engine.core.orders import Side


def slippage_price(execution_price: float, benchmark_price: float, side: Side | str) -> float:
    """Return side-aware slippage in price units."""

    side = Side.from_value(side)
    if execution_price <= 0 or benchmark_price <= 0:
        raise ValueError("Execution and benchmark prices must be positive.")
    return execution_price - benchmark_price if side is Side.BUY else benchmark_price - execution_price


def slippage_bps(execution_price: float, benchmark_price: float, side: Side | str) -> float:
    """Return side-aware slippage in basis points."""

    return slippage_price(execution_price, benchmark_price, side) / benchmark_price * 10_000


def benchmark_vwap(prices: Sequence[float], quantities: Sequence[float]) -> float:
    """Return volume-weighted average price."""

    prices_arr = np.asarray(prices, dtype="float64")
    qty_arr = np.asarray(quantities, dtype="float64")
    if len(prices_arr) != len(qty_arr):
        raise ValueError("Prices and quantities must have the same length.")
    if qty_arr.sum() <= 0:
        raise ValueError("Total quantity must be positive.")
    return float(np.average(prices_arr, weights=qty_arr))


def benchmark_twap(prices: Sequence[float]) -> float:
    """Return time-weighted average price."""

    prices_arr = np.asarray(prices, dtype="float64")
    if len(prices_arr) == 0:
        raise ValueError("At least one price is required.")
    return float(np.mean(prices_arr))


def implementation_shortfall(avg_execution_price: float, arrival_price: float, side: Side | str) -> float:
    """Return implementation shortfall in basis points against arrival price."""

    return slippage_bps(avg_execution_price, arrival_price, side)


def execution_quality_table(rows: list[dict[str, object]]) -> pd.DataFrame:
    """Return a normalized execution-quality summary table."""

    return pd.DataFrame(rows)
