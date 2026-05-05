from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderStatus, OrderType, Side


def test_crossing_limit_buy_executes_immediately():
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 10, 100.0))
    result = engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 6, 100.0))
    assert result.trade_count == 1
    assert result.order.status is OrderStatus.FILLED


def test_crossing_limit_sell_executes_immediately():
    engine = MatchingEngine()
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 10, 100.0))
    result = engine.process_order(Order("S1", Side.SELL, OrderType.LIMIT, 6, 100.0))
    assert result.trade_count == 1
    assert result.trades[0].price == 100.0


def test_non_crossing_limit_order_rests():
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 10, 100.1))
    result = engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 6, 100.0))
    assert result.trade_count == 0
    assert engine.book.get_order("B1") is not None
