"""Run a small order book demonstration."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lob_engine.analytics.microstructure import book_metrics
from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderType, Side


def main() -> None:
    engine = MatchingEngine()
    orders = [
        Order("B-001", Side.BUY, OrderType.LIMIT, 120, 99.95, timestamp=1),
        Order("B-002", Side.BUY, OrderType.LIMIT, 80, 99.90, timestamp=2),
        Order("A-001", Side.SELL, OrderType.LIMIT, 100, 100.05, timestamp=3),
        Order("A-002", Side.SELL, OrderType.LIMIT, 75, 100.10, timestamp=4),
    ]
    for order in orders:
        engine.process_order(order)

    print("Top-of-book metrics")
    for key, value in book_metrics(engine.book).items():
        print(f"{key}: {value}")
    print("\nOrder book ladder")
    print(engine.book.top_n_levels(5).to_string(index=False))


if __name__ == "__main__":
    main()
