from lob_engine.core.order_book import LimitOrderBook
from lob_engine.core.orders import Order, OrderStatus, OrderType, Side


def test_add_order_and_lookup():
    book = LimitOrderBook()
    order = Order("B1", Side.BUY, OrderType.LIMIT, 100, 99.9)
    book.add_order(order)
    assert book.get_order("B1") is order
    assert len(book) == 1


def test_best_bid_ask_spread_mid_depth():
    book = LimitOrderBook()
    book.add_order(Order("B1", Side.BUY, OrderType.LIMIT, 100, 99.9))
    book.add_order(Order("A1", Side.SELL, OrderType.LIMIT, 80, 100.1))
    assert book.best_bid() == 99.9
    assert book.best_ask() == 100.1
    assert round(book.spread(), 2) == 0.2
    assert book.mid_price() == 100.0
    assert book.depth_at_price(Side.BUY, 99.9) == 100


def test_fifo_queue_same_price():
    book = LimitOrderBook()
    older = Order("B-old", Side.BUY, OrderType.LIMIT, 10, 99.9, timestamp=1)
    newer = Order("B-new", Side.BUY, OrderType.LIMIT, 10, 99.9, timestamp=2)
    book.add_order(older)
    book.add_order(newer)
    assert [order.order_id for order in book.iter_orders(Side.BUY)] == ["B-old", "B-new"]


def test_cancel_order_removes_order():
    book = LimitOrderBook()
    order = Order("B1", Side.BUY, OrderType.LIMIT, 10, 99.9)
    book.add_order(order)
    removed, cancelled = book.cancel_order("B1")
    assert removed
    assert cancelled.status is OrderStatus.CANCELLED
    assert book.get_order("B1") is None
