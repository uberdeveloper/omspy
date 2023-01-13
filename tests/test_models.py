from omspy.models import *
import pytest
from unittest.mock import patch


@pytest.fixture
def order_lock():
    return OrderLock()


@pytest.fixture
def orderbook():
    bids = [
        Quote(price=6466, quantity=3, orders_count=3),
        Quote(price=6465, quantity=29, orders_count=19),
        Quote(price=6464, quantity=43, orders_count=33),
        Quote(price=6463, quantity=19, orders_count=12),
        Quote(price=6462, quantity=11, orders_count=8),
    ]

    asks = [
        Quote(price=6468, quantity=4, orders_count=4),
        Quote(price=6469, quantity=17, orders_count=3),
        Quote(price=6470, quantity=6, orders_count=3),
        Quote(price=6471, quantity=13, orders_count=11),
        Quote(price=6472, quantity=43, orders_count=20),
    ]
    return OrderBook(bid=bids, ask=asks)


def test_basic_position():
    position = BasicPosition(symbol="AAPL")
    assert position.symbol == "AAPL"


def test_basic_position_calculations():
    position = BasicPosition(
        symbol="AAPL",
        buy_quantity=100,
        sell_quantity=120,
        buy_value=100 * 131,
        sell_value=120 * 118.5,
    )
    assert position.net_quantity == -20
    assert position.average_buy_value == 131
    assert position.average_sell_value == 118.5


def test_basic_position_zero_quantity():
    position = BasicPosition(symbol="AAPL")
    assert position.average_buy_value == 0
    assert position.average_sell_value == 0
    position.buy_quantity = 10
    assert position.average_buy_value == 0
    position.buy_value = 1315
    assert position.average_buy_value == 131.5
    assert position.average_sell_value == 0


def test_order_book():
    bids = [Quote(price=120, quantity=4), Quote(price=121, quantity=20, orders_count=2)]
    asks = [Quote(price=119, quantity=7), Quote(price=118, quantity=28)]
    orderbook = OrderBook(bid=bids, ask=asks)
    assert orderbook.bid[0].quantity == 4
    assert orderbook.bid[0].orders_count is None
    assert orderbook.bid[-1].orders_count == 2
    assert orderbook.ask[1].quantity == 28
    assert orderbook.ask[-1].value == 118 * 28


@patch("pendulum.now")
def test_order_lock_defaults(now):
    known = pendulum.datetime(2022, 1, 1, 10, 10, 13, tz=None)
    now.side_effect = [known] * 6
    lock = OrderLock()
    assert lock.creation_lock_till == known
    assert lock.modification_lock_till == known
    assert lock.cancellation_lock_till == known


def test_order_lock_methods():
    known = pendulum.datetime(2022, 1, 1, 10, 10, 15, tz=None)
    lock = OrderLock()
    with pendulum.test(known):
        lock.create(20)
        assert lock.creation_lock_till == known.add(seconds=20)
    with pendulum.test(known):
        lock.modify(60)
        assert lock.modification_lock_till == pendulum.datetime(
            2022, 1, 1, 10, 11, 15, tz=None
        )
        lock.cancel(15)
        assert lock.cancellation_lock_till == pendulum.datetime(
            2022, 1, 1, 10, 10, 30, tz=None
        )


def test_order_lock_methods_max_duration():
    known = pendulum.datetime(2022, 1, 1, 10, 10, 15, tz=None)
    lock = OrderLock()
    with pendulum.test(known):
        lock.create(90)
        assert lock.creation_lock_till == pendulum.datetime(
            2022, 1, 1, 10, 11, 15, tz=None
        )
        lock.max_order_creation_lock_time = 120
        lock.create(90)
        assert lock.creation_lock_till == pendulum.datetime(
            2022, 1, 1, 10, 11, 45, tz=None
        )


@pytest.mark.parametrize("method", ["can_create", "can_modify", "can_cancel"])
def test_order_lock_can_methods(method):
    known = pendulum.datetime(2022, 1, 1, 10, 10, 15, tz=None)
    with pendulum.test(known):
        lock = OrderLock()
        assert getattr(lock, method) is False
    with pendulum.test(known.add(seconds=1)):
        assert getattr(lock, method) is True
        assert getattr(lock, method[4:])(10)
        assert getattr(lock, method) is False
    with pendulum.test(known.add(seconds=12)):
        assert getattr(lock, method) is True


def test_orderbook_is_bid_ask():
    ob = OrderBook(bid=[], ask=[])
    assert ob.is_bid_ask is False
    ob.bid.append(Quote(price=100, quantity=10, orders_count=175))
    assert ob.is_bid_ask is False
    ob.ask.append(Quote(price=100, quantity=10, orders_count=175))
    assert ob.is_bid_ask is True


def test_orderbook_spread(orderbook):
    assert orderbook.spread == 2
    ob = OrderBook(bid=[], ask=[])
    assert ob.spread == 0
