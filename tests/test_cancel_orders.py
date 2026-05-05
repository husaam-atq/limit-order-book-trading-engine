from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import CancelRequest, Order, OrderType, Side


def test_cancel_existing_order():
    engine = MatchingEngine()
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 10, 99.9))
    result = engine.process_cancel(CancelRequest("C1", 1.0, "B1"))
    assert result.accepted
    assert engine.book.get_order("B1") is None


def test_cancel_unknown_order_rejected():
    engine = MatchingEngine()
    result = engine.process_cancel(CancelRequest("C1", 1.0, "missing"))
    assert not result.accepted
    assert "not found" in result.message
