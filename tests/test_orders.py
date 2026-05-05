import pytest

from lob_engine.core.orders import Order, OrderStatus, OrderType, Side


def test_valid_order_creation():
    order = Order("O1", "buy", "limit", 100, 99.5, timestamp=1.0)
    assert order.side is Side.BUY
    assert order.order_type is OrderType.LIMIT
    assert order.remaining_quantity == 100
    assert order.status is OrderStatus.NEW


@pytest.mark.parametrize(
    "kwargs",
    [
        {"quantity": 0, "price": 1.0},
        {"quantity": -1, "price": 1.0},
        {"quantity": 1, "price": -1.0},
        {"quantity": 1, "price": None},
    ],
)
def test_invalid_limit_order_rejected(kwargs):
    with pytest.raises(ValueError):
        Order("BAD", Side.BUY, OrderType.LIMIT, timestamp=1.0, **kwargs)


def test_invalid_side_and_type_rejected():
    with pytest.raises(ValueError):
        Order("BAD", "hold", OrderType.LIMIT, 1, 1.0)
    with pytest.raises(ValueError):
        Order("BAD2", Side.BUY, "iceberg", 1, 1.0)


def test_market_order_does_not_require_price():
    order = Order("M1", Side.SELL, OrderType.MARKET, 25, timestamp=1.0)
    assert order.price is None


def test_status_lifecycle():
    order = Order("O1", Side.BUY, OrderType.LIMIT, 10, 99.0)
    order.record_fill(4)
    assert order.status is OrderStatus.PARTIALLY_FILLED
    assert order.remaining_quantity == 6
    order.record_fill(6)
    assert order.status is OrderStatus.FILLED
    assert order.filled_quantity == 10
