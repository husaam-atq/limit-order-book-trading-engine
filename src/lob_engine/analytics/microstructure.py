"""Market microstructure analytics for visible limit order book data."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Optional

import numpy as np
import pandas as pd

from lob_engine.core.order_book import LimitOrderBook
from lob_engine.core.orders import Side


def order_book_imbalance(book: LimitOrderBook, levels: int = 1) -> float:
    """Return bid/ask quantity imbalance in [-1, 1]."""

    bid_depth = book.total_depth(Side.BUY, levels)
    ask_depth = book.total_depth(Side.SELL, levels)
    total = bid_depth + ask_depth
    return 0.0 if total == 0 else (bid_depth - ask_depth) / total


def volume_imbalance(buy_volume: float, sell_volume: float) -> float:
    """Return signed trade volume imbalance in [-1, 1]."""

    total = buy_volume + sell_volume
    return 0.0 if total == 0 else (buy_volume - sell_volume) / total


def weighted_mid_price(book: LimitOrderBook) -> Optional[float]:
    """Return liquidity-weighted midpoint using top-of-book sizes."""

    bid = book.best_bid()
    ask = book.best_ask()
    bid_size = book.best_bid_size()
    ask_size = book.best_ask_size()
    if bid is None or ask is None or bid_size + ask_size == 0:
        return None
    return (ask * bid_size + bid * ask_size) / (bid_size + ask_size)


def depth_by_level(book: LimitOrderBook, levels: int = 5) -> pd.DataFrame:
    """Return a normalized bid/ask depth table."""

    bids = book.depth_levels(Side.BUY, levels)
    asks = book.depth_levels(Side.SELL, levels)
    rows = []
    for rank, level in enumerate(bids, start=1):
        rows.append(
            {
                "level": rank,
                "side": "bid",
                "price": level.price,
                "quantity": level.quantity,
                "orders": level.order_count,
            }
        )
    for rank, level in enumerate(asks, start=1):
        rows.append(
            {
                "level": rank,
                "side": "ask",
                "price": level.price,
                "quantity": level.quantity,
                "orders": level.order_count,
            }
        )
    return pd.DataFrame(rows, columns=["level", "side", "price", "quantity", "orders"])


def book_pressure(book: LimitOrderBook, levels: int = 5) -> float:
    """Return a distance-weighted order book pressure score in [-1, 1]."""

    bid_score = 0.0
    ask_score = 0.0
    for idx, level in enumerate(book.depth_levels(Side.BUY, levels), start=1):
        bid_score += level.quantity / idx
    for idx, level in enumerate(book.depth_levels(Side.SELL, levels), start=1):
        ask_score += level.quantity / idx
    total = bid_score + ask_score
    return 0.0 if total == 0 else (bid_score - ask_score) / total


def effective_spread(trade_price: float, mid_price: float, side: Side | str) -> float:
    """Return signed effective spread in price units."""

    side = Side.from_value(side)
    if trade_price <= 0 or mid_price <= 0:
        raise ValueError("Trade and mid prices must be positive.")
    if side is Side.BUY:
        return 2.0 * (trade_price - mid_price)
    return 2.0 * (mid_price - trade_price)


def realised_spread(trade_price: float, future_mid_price: float, side: Side | str) -> float:
    """Return realised spread against a future midpoint."""

    side = Side.from_value(side)
    if trade_price <= 0 or future_mid_price <= 0:
        raise ValueError("Prices must be positive.")
    if side is Side.BUY:
        return 2.0 * (trade_price - future_mid_price)
    return 2.0 * (future_mid_price - trade_price)


def trade_intensity(trade_timestamps: Sequence[float], window: float) -> pd.Series:
    """Return rolling trade count per time window for ordered timestamps."""

    if window <= 0:
        raise ValueError("Window must be positive.")
    series = pd.Series(1, index=pd.to_timedelta(trade_timestamps, unit="s"))
    return series.rolling(f"{window}s").sum().reset_index(drop=True)


def rolling_volatility(mid_prices: Sequence[float], window: int = 20) -> pd.Series:
    """Return rolling standard deviation of log midpoint returns."""

    if window <= 1:
        raise ValueError("Window must be greater than one.")
    prices = pd.Series(mid_prices, dtype="float64").replace(0, np.nan).ffill()
    log_returns = np.log(prices).diff()
    return log_returns.rolling(window).std()


def rolling_order_flow_imbalance(
    buy_quantities: Sequence[float], sell_quantities: Sequence[float], window: int = 20
) -> pd.Series:
    """Return rolling order-flow imbalance from buy and sell quantities."""

    if window <= 0:
        raise ValueError("Window must be positive.")
    buys = pd.Series(buy_quantities, dtype="float64")
    sells = pd.Series(sell_quantities, dtype="float64")
    numerator = buys.rolling(window).sum() - sells.rolling(window).sum()
    denominator = buys.rolling(window).sum() + sells.rolling(window).sum()
    return (numerator / denominator.replace(0, np.nan)).fillna(0.0)


def book_metrics(book: LimitOrderBook, levels: int = 5) -> dict[str, Optional[float]]:
    """Return common top-of-book and liquidity metrics."""

    bid_depth = book.total_depth(Side.BUY, levels)
    ask_depth = book.total_depth(Side.SELL, levels)
    spread = book.spread()
    mid = book.mid_price()
    return {
        "best_bid": book.best_bid(),
        "best_ask": book.best_ask(),
        "mid_price": mid,
        "spread": spread,
        "spread_bps": None if spread is None or mid in (None, 0) else spread / mid * 10_000,
        "bid_depth": float(bid_depth),
        "ask_depth": float(ask_depth),
        "imbalance": order_book_imbalance(book, levels),
        "weighted_mid": weighted_mid_price(book),
        "book_pressure": book_pressure(book, levels),
        "is_crossed": (
            math.nan
            if book.best_bid() is None or book.best_ask() is None
            else float(book.best_bid() >= book.best_ask())
        ),
    }
