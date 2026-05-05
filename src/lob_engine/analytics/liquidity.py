"""Liquidity summaries and depth transforms."""

from __future__ import annotations

import pandas as pd

from lob_engine.core.order_book import LimitOrderBook
from lob_engine.core.orders import Side


def top_n_liquidity(book: LimitOrderBook, levels: int = 5) -> dict[str, int]:
    """Return aggregate visible depth on both sides over the top N levels."""

    return {
        "bid_liquidity": book.total_depth(Side.BUY, levels),
        "ask_liquidity": book.total_depth(Side.SELL, levels),
        "total_liquidity": book.total_depth(Side.BUY, levels) + book.total_depth(Side.SELL, levels),
    }


def depth_curve(book: LimitOrderBook, levels: int = 10) -> pd.DataFrame:
    """Return cumulative depth by level for both sides."""

    rows = []
    for side in (Side.BUY, Side.SELL):
        cumulative = 0
        for rank, level in enumerate(book.depth_levels(side, levels), start=1):
            cumulative += level.quantity
            rows.append(
                {
                    "side": side.value,
                    "level": rank,
                    "price": level.price,
                    "quantity": level.quantity,
                    "cumulative_quantity": cumulative,
                }
            )
    return pd.DataFrame(rows)


def liquidity_gap(book: LimitOrderBook) -> float | None:
    """Return top-of-book spread as a simple liquidity gap proxy."""

    return book.spread()
