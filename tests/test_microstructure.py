from lob_engine.analytics.microstructure import (
    book_metrics,
    depth_by_level,
    order_book_imbalance,
    rolling_order_flow_imbalance,
    rolling_volatility,
    weighted_mid_price,
)
from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderType, Side


def _book():
    engine = MatchingEngine()
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 100, 99.9))
    engine.process_order(Order("B2", Side.BUY, OrderType.LIMIT, 50, 99.8))
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 75, 100.1))
    return engine.book


def test_imbalance_weighted_mid_depth_metrics():
    book = _book()
    assert round(order_book_imbalance(book, 1), 6) == round(25 / 175, 6)
    assert weighted_mid_price(book) is not None
    metrics = book_metrics(book)
    assert metrics["best_bid"] == 99.9
    assert len(depth_by_level(book, 2)) == 3


def test_rolling_metrics():
    vol = rolling_volatility([100, 100.1, 100.2, 100.3, 100.4], window=3)
    ofi = rolling_order_flow_imbalance([10, 20, 30], [5, 5, 5], window=2)
    assert len(vol) == 5
    assert ofi.iloc[-1] > 0
