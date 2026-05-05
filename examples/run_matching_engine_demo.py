"""Run a matching-engine demonstration with partial fills."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderType, Side


def main() -> None:
    engine = MatchingEngine()
    engine.process_order(Order("ASK-1", Side.SELL, OrderType.LIMIT, 50, 100.01, timestamp=1))
    engine.process_order(Order("ASK-2", Side.SELL, OrderType.LIMIT, 80, 100.02, timestamp=2))
    engine.process_order(Order("BID-1", Side.BUY, OrderType.LIMIT, 70, 99.99, timestamp=3))
    result = engine.process_order(Order("BUY-MKT", Side.BUY, OrderType.MARKET, 100, timestamp=4))

    print(result.message)
    print(engine.trades_frame().to_string(index=False))
    print("\nRemaining book")
    print(engine.book.top_n_levels(5).to_string(index=False))


if __name__ == "__main__":
    main()
