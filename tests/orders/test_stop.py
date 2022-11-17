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
def trailing_stop_dict():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10100)
        stop_limit_order = dict(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type=("LIMIT", "SL-M"),
            trigger_price=850,
            trail_by=10,
            broker=broker,
        )
        return stop_limit_order


@pytest.fixture
def order_dict():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10100)
        return dict(
            symbol="aapl",
            side="buy",
            quantity=100,
            price=930,
            order_type=("LIMIT", "SL-M"),
            trigger_price=850,
            broker=broker,
        )


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


def test_trailing_stop_defaults(trailing_stop_dict):
    order = TrailingStopOrder(**trailing_stop_dict)
    assert order._stop_loss == 850
    assert order._next_trail == 940
    trailing_stop_dict.update({"side": "sell", "price": 900, "trigger_price": 950})
    order = TrailingStopOrder(**trailing_stop_dict)
    assert order._stop_loss == 950
    assert order._next_trail == 890


def test_trailing_stop_market_order(trailing_stop_dict):
    dct = trailing_stop_dict
    dct["price"] = 0
    dct["order_type"] = ("MARKET", "SL-M")
    order = TrailingStopOrder(**trailing_stop_dict)
    assert order._stop_loss == 850
    assert order._next_trail == 0


def test_trailing_stop_run_buy(trailing_stop_dict):
    dct = trailing_stop_dict
    order = TrailingStopOrder(**trailing_stop_dict)
    ltps = (935, 940, 941, 955, 940, 948, 961, 930)
    sl = (850, 850, 860, 870, 870, 870, 880, 880)
    for l, s in zip(ltps, sl):
        order.run(ltp=l)
        assert order._stop_loss == s
        assert order.orders[-1].trigger_price == s
    assert order.broker.order_modify.call_count == 3


def test_trailing_stop_run_sell(trailing_stop_dict):
    dct = trailing_stop_dict
    dct.update({"side": "sell", "trigger_price": 1000})
    order = TrailingStopOrder(**trailing_stop_dict)
    ltps = (930, 950, 980, 917, 894, 897, 920, 887)
    sl = (1000, 1000, 1000, 990, 980, 970, 970, 960)
    for l, s in zip(ltps, sl):
        order.run(ltp=l)
        print(l, s)
        assert order._stop_loss == s
        assert order.orders[-1].trigger_price == s
    assert order.broker.order_modify.call_count == 4


def test_trailing_stop_run_no_price(trailing_stop_dict):
    dct = trailing_stop_dict
    dct["price"] = 0
    dct["order_type"] = ("MARKET", "SL-M")
    order = TrailingStopOrder(**trailing_stop_dict)
    ltps = (935, 940, 941, 955, 940, 948, 961, 930)
    for l in ltps:
        order.run(ltp=l)
        assert order.orders[-1].trigger_price == 850


def test_target_order_defaults(order_dict):
    order_dict["target"] = 950
    order = TargetOrder(**order_dict)
    order.execute_all()
    assert order.orders[0].order_type == "LIMIT"
    assert order.orders[0].price == 930
    assert order.orders[-1].order_type == "SL-M"
    assert order.orders[-1].trigger_price == 850


def test_target_order_buy_target_hit(order_dict):
    order_dict["target"] = 950
    order = TargetOrder(**order_dict)
    order.execute_all()
    for ltp in (930, 944, 910, 864, 930, 940, 950):
        order.run(ltp=ltp)
    assert order.broker.order_place.call_count == 2
    order.broker.order_modify.assert_called_once()
    # TODO: Check do not hit target after SL hit
    # TODO: Do not call target after modify hit


def test_target_order_sell_target_hit(order_dict):
    order_dict.update({"side": "sell", "price": 830, "target": 800})
    order = TargetOrder(**order_dict)
    order.execute_all()
    for ltp in (830, 817, 824, 801, 800):
        order.run(ltp=ltp)
    assert order.broker.order_place.call_count == 2
    order.broker.order_modify.assert_called_once()
