from omspy.algos.trailing import *
import pytest
import pendulum
from omspy.order import CompoundOrder, Order


@pytest.fixture
def simple():
    known = pendulum.datetime(2025, 1, 1, tz="local")
    with pendulum.travel_to(known):
        return Trailing(
            start_time=known.add(hours=9),
            end_time=known.now().add(hours=15),
            start_trailing_at=1000,
            trailing_stop=500,
            trailing_step=300,
        )


def test_defaults(simple):
    s = simple
    assert s.start_time == pendulum.datetime(2025, 1, 1, 9, tz="local")
    assert s.end_time == pendulum.datetime(2025, 1, 1, 15, tz="local")
    assert s.start_trailing_at == 1000
    assert s.trailing_stop == 500
    assert s.trailing_step == 300
    assert isinstance(s.order, CompoundOrder)


def test_trailing_with_order():
    co = CompoundOrder()
    order1 = Order(symbol="AAPL", side="BUY", quantity=100)
    co.add(order1)
    order2 = Order(symbol="AAPL", side="SELL", quantity=100)
    co.add(order2)
    trailing = Trailing(
        start_time=pendulum.now(), end_time=pendulum.now().add(hours=15), order=co
    )
    assert trailing.order == co
    assert id(co.orders[0]) == id(order1) == id(trailing.order.orders[0])
    assert id(co.orders[1]) == id(order2) == id(trailing.order.orders[1])
