from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderStatus, OrderType, Side


def test_market_buy_consumes_asks_lowest_upward():
    engine = MatchingEngine()
    engine.process_order(Order("A2", Side.SELL, OrderType.LIMIT, 10, 100.2, timestamp=1))
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 10, 100.1, timestamp=2))
    result = engine.process_order(Order("MB", Side.BUY, OrderType.MARKET, 12, timestamp=3))
    assert [trade.price for trade in result.trades] == [100.1, 100.2]
    assert [trade.quantity for trade in result.trades] == [10, 2]


def test_market_remainder_cancelled_when_liquidity_exhausted():
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 5, 100.1))
    result = engine.process_order(Order("MB", Side.BUY, OrderType.MARKET, 8))
    assert result.order.status is OrderStatus.CANCELLED
    assert result.order.remaining_quantity == 3
