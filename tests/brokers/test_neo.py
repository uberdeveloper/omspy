from pathlib import PurePath
from omspy.brokers.neo import *
import pendulum
import pytest
import json
from unittest.mock import patch, call


@pytest.fixture
def mock_neo():
    broker = Neo(
        "consumer_key", "consumer_secret", "mobilenumber", "password", "two_fa"
    )
    with patch("neo_api_client.NeoAPI") as mock_broker:
        broker.neo = mock_broker
        return broker


@pytest.fixture
def mock_data():
    # mock data for neo
    with open("tests/data/kotak_neo.json") as f:
        dct = json.load(f)
        return dct


@patch("neo_api_client.NeoAPI")
def test_authenticate(mock_broker):
    broker = Neo(
        "consumer_key",
        "consumer_secret",
        mobilenumber="+9112345678",
        password="password",
        twofa=1111,
    )
    broker.neo = mock_broker
    broker.authenticate()
    mock_broker.login.assert_called_once()
    mock_broker.session_2fa.assert_called_once()


def test_order_place(mock_neo):
    broker = mock_neo
    broker.order_place(symbol="SBIN-EQ", side="buy", quantity=1)
    broker.neo.place_order.assert_called_once()
    expected = dict(
        exchange_segment="NSE",
        product="MIS",
        price="0",
        order_type="MKT",
        quantity="1",
        validity="DAY",
        trading_symbol="SBIN-EQ",
        transaction_type="B",
        disclosed_quantity="0",
        trigger_price="0",
    )
    call_list = broker.neo.place_order.call_args_list
    assert call_list[0].kwargs == expected


def test_order_modify(mock_neo):
    broker = mock_neo
    broker.order_place(symbol="SBIN-EQ", side="buy", quantity=1)
    broker.neo.place_order.assert_called_once()
    broker.order_modify(order_id="12345678", quantity=10, price=100)
    expected = dict(
        order_id="12345678",
        quantity="10",
        price="100",
        amo="NO",
        product="MIS",
        validity="DAY",
    )
    broker.neo.modify_order.assert_called_once()
    call_list = broker.neo.modify_order.call_args_list
    assert call_list[0].kwargs == expected


def test_order_cancel(mock_neo):
    broker = mock_neo
    broker.order_cancel(12345678)
    broker.neo.cancel_order.assert_called_once()


def test_orders(mock_neo, mock_data):
    mock_neo.neo.order_report.side_effect = [mock_data["orders"]] * 4
    broker = mock_neo
    orders = broker.orders
    assert len(orders) == 2
    for key in ("order_id", "symbol", "status", "product"):
        for order in orders:
            assert key in order


def test_orders_no_data(mock_neo, mock_data):
    mock_neo.neo.order_report.side_effect = dict(
        stat="failure", reason="wrong connection"
    )
    broker = mock_neo
    orders = broker.orders
    assert orders == [{}]
