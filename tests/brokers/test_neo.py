from pathlib import PurePath
from omspy.brokers.neo import *
import pendulum
import pytest
import json
from unittest.mock import patch, call


@pytest.fixture
def mock_neo():
    broker = Neo("consumer_key", "consumer_secret", "user_id", "password", "two_fa")
    with patch("neo_api_client.NeoAPI") as mock_broker:
        broker.neo = mock_broker
        return broker


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
