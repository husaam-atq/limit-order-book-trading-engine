from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderStatus, OrderType, Side


def test_trade_records_include_maker_taker_and_remaining():
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 10, 100.0, timestamp=1))
    result = engine.process_order(Order("B1", Side.BUY, OrderType.MARKET, 4, timestamp=2))
    trade = result.trades[0]
    assert trade.maker_order_id == "A1"
    assert trade.taker_order_id == "B1"
    assert trade.aggressor_remaining == 0
    assert trade.passive_remaining == 6


def test_market_sell_hits_best_bid():
    engine = MatchingEngine()
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 5, 100.0, timestamp=1))
    result = engine.process_order(Order("S1", Side.SELL, OrderType.MARKET, 5, timestamp=2))
    assert result.order.status is OrderStatus.FILLED
    assert result.trades[0].price == 100.0


def test_duplicate_order_id_rejected():
    engine = MatchingEngine()
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 5, 100.0))
    result = engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 5, 99.0))
    assert not result.accepted
    assert result.order.status is OrderStatus.REJECTED
