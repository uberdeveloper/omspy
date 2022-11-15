import pytest
from unittest.mock import patch, call
from collections import Counter
import pendulum
import yaml
from copy import deepcopy
from omspy.brokers.zerodha import Zerodha
from omspy.orders.stop import *


@pytest.fixture
def stop_order():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10100)
        stop_order = StopOrder(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type=("LIMIT", "SL-M"),
            trigger_price=850,
            broker=broker,
        )
        return stop_order


@pytest.fixture
def stop_limit_order():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10100)
        stop_limit_order = StopLimitOrder(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type=("LIMIT", "SL-M"),
            trigger_price=850,
            stop_limit_price=830,
            broker=broker,
        )
        return stop_limit_order


@pytest.fixture
def trailing_stop_order():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = TrailingStopOrder(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type="LIMIT",
            trigger_price=850,
            trail_by=10,
            broker=broker,
        )
        order.orders[0].filled_quantity = 100
        order.orders[0].pending_quantity = 0
        order.orders[0].status = "COMPLETE"
        order.orders[0].average_price = 930
        return order


def test_stop_order(stop_order):
    assert stop_order.count == 2
    assert stop_order.orders[0].order_type == "LIMIT"
    order = Order(
        symbol="aapl",
        side="sell",
        quantity=100,
        trigger_price=850,
        price=930,
        order_type="SL-M",
        parent_id=stop_order.id,
    )
    # Copy over from existing order as these are system attributes
    order.id = stop_order.orders[-1].id
    order.timestamp = stop_order.orders[-1].timestamp
    assert stop_order.orders[-1] == order
    assert [o.order_type for o in stop_order.orders] == ["LIMIT", "SL-M"]


def test_stop_order_execute_all(stop_order):
    broker = stop_order.broker
    stop_order.execute_all()
    assert broker.order_place.call_count == 2
    assert stop_order.orders[0].order_id == 10000
    assert stop_order.orders[1].order_id == 10001
    for i in range(10):
        stop_order.execute_all()
    assert broker.order_place.call_count == 2


def test_stop_limit_order_defaults(stop_limit_order):
    order = stop_limit_order
    assert len(order.orders) == 2
    assert [o.order_type for o in order.orders] == ["LIMIT", "SL"]
    assert [o.price for o in order.orders] == [930, 830]
    assert [o.trigger_price for o in order.orders] == [0, 850]
    assert [o.side for o in order.orders] == ["buy", "sell"]


def test_stop_limit_order_execute_all(stop_limit_order):
    broker = stop_limit_order.broker
    stop_limit_order.execute_all()
    assert broker.order_place.call_count == 2
    print(stop_limit_order.orders[0])
    assert stop_limit_order.orders[0].order_id == 10000
    assert stop_limit_order.orders[1].order_id == 10001
    for i in range(10):
        stop_limit_order.execute_all()
    assert broker.order_place.call_count == 2
    # TODO: add test for order_type
    # TODO: add test for side
