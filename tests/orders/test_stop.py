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
        stop_order = StopOrder(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type="LIMIT",
            trigger_price=850,
            broker=broker,
        )
        return stop_order


@pytest.fixture
def bracket_order():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        bracket_order = BracketOrder(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type="LIMIT",
            trigger_price=850,
            broker=broker,
            target=960,
        )
        return bracket_order


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
            trail_by=(10, 5),
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
        price=0,
        order_type="SL-M",
        parent_id=stop_order.id,
    )
    # Copy over from existing order as these are system attributes
    order.id = stop_order.orders[-1].id
    order.timestamp = stop_order.orders[-1].timestamp
    assert stop_order.orders[-1] == order


def test_stop_order_execute_all(stop_order):
    broker = stop_order.broker
    stop_order.broker.order_place.side_effect = ["aaaaaa", "bbbbbb"]
    stop_order.execute_all()
    assert broker.order_place.call_count == 2
    assert stop_order.orders[0].order_id == "aaaaaa"
    assert stop_order.orders[1].order_id == "bbbbbb"
    for i in range(10):
        stop_order.execute_all()
    assert broker.order_place.call_count == 2


def test_bracket_order_is_target_hit(bracket_order):
    broker = bracket_order.broker
    bracket_order.broker.order_place.side_effect = ["aaaaaa", "bbbbbb"]
    bracket_order.execute_all()
    assert broker.order_place.call_count == 2
    bracket_order.update_orders(
        {"aaaaaa": {"average_price": 930, "filled_quantity": 100, "status": "COMPLETE"}}
    )
    bracket_order.update_ltp({"aapl": 944})
    assert bracket_order.is_target_hit is False
    bracket_order.update_ltp({"aapl": 961})
    assert bracket_order.is_target_hit is True
    assert bracket_order.total_mtm == 3100


def test_bracket_order_do_target(bracket_order):
    broker = bracket_order.broker
    bracket_order.broker.order_place.side_effect = ["aaaaaa", "bbbbbb"]
    bracket_order.execute_all()
    bracket_order.update_orders(
        {"aaaaaa": {"average_price": 930, "filled_quantity": 100, "status": "COMPLETE"}}
    )
    for i in (944, 952, 960, 961):
        bracket_order.update_ltp({"aapl": i})
        bracket_order.do_target()
    broker.order_modify.assert_called_once()
    # TO DO: Add kwargs to check


def test_trailing_stop_order_update_mtm(trailing_stop_order):
    order = trailing_stop_order
    order._update_maxmtm()
    assert order.maxmtm == 0

    order.update_ltp({"aapl": 940})
    order._update_maxmtm()
    assert order.maxmtm == 1000

    order.update_ltp({"aapl": 920})
    order._update_maxmtm()
    assert order.maxmtm == 1000
    assert order.total_mtm == -1000


def test_trailing_stop_update_stop(trailing_stop_order):
    order = trailing_stop_order
    order.update_ltp({"aapl": 940})
    order._update_maxmtm()
    order._update_stop()
    assert order.maxmtm == 1000
    assert order.stop == 855

    order.update_ltp({"aapl": 990})
    order._update_maxmtm()
    order._update_stop()
    assert order.stop == 880

    order.update_ltp({"aapl": 900})
    order._update_maxmtm()
    order._update_stop()
    assert order.stop == 880
    assert order.maxmtm == 6000
    assert order.total_mtm == -3000


def test_trailing_stop_update_stop_two(trailing_stop_order):
    order = trailing_stop_order
    order.update_ltp({"aapl": 940})
    order._update_maxmtm()
    order._update_stop()
    assert order.maxmtm == 1000
    assert order.stop == 855

    # Change trailing order settings
    order.trail_big = 10
    order.trail_small = 10
    order.update_ltp({"aapl": 990})
    order._update_maxmtm()
    order._update_stop()
    assert order.stop == 910


def test_trailing_stop_watch(trailing_stop_order):
    order = trailing_stop_order
    broker = order.broker
    order.update_ltp({"aapl": 1000})
    order.trail_big = 10
    order.trail_small = 10
    order.watch()
    assert order.stop == 920
    for i in (944, 912, 960, 961):
        order.update_ltp({"aapl": i})
        order.watch()
    broker.order_modify.assert_called_once()


def test_stop_limit_order():
    broker = Broker()
    order = StopLimitOrder(
        symbol="aapl", side="buy", quantity=100, trigger_price=850, broker=broker
    )
    assert order.orders[-1].price == 850
    order = StopLimitOrder(
        symbol="aapl",
        side="buy",
        quantity=100,
        trigger_price=850,
        stop_limit_price=855,
        broker=broker,
    )
    assert order.orders[-1].price == 855
