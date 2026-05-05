from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderStatus, OrderType, Side


def test_multi_level_partial_fill():
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 5, 100.0))
    engine.process_order(Order("A2", Side.SELL, OrderType.LIMIT, 5, 100.1))
    result = engine.process_order(Order("MB", Side.BUY, OrderType.MARKET, 8))
    assert [trade.quantity for trade in result.trades] == [5, 3]
    assert engine.book.depth_at_price(Side.SELL, 100.1) == 2


def test_limit_remainder_rests_after_partial_fill():
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 5, 100.0))
    result = engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 8, 101.0))
    assert result.order.status is OrderStatus.PARTIALLY_FILLED
    assert engine.book.get_order("B1").remaining_quantity == 3
