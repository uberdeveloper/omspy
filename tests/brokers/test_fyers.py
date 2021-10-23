from omspy.brokers.fyers import Fyers
from unittest.mock import patch
import pytest
import json
from copy import deepcopy

with open("tests/data/fyers.json") as f:
    mock_data = json.load(f)


@pytest.fixture
def mock_fyers():
    broker = Fyers("app_id", "secret", "user_id", "password", "pan")
    with patch("fyers_api.fyersModel.FyersModel") as mock:
        broker.fyers = mock
    return broker


def test_profile(mock_fyers):
    broker = mock_fyers
    broker.fyers.get_profile.return_value = mock_data.get("profile")
    profile = broker.profile
    broker.fyers.get_profile.assert_called_once()
    assert profile == mock_data.get("profile")


def test_funds(mock_fyers):
    broker = mock_fyers
    broker.fyers.funds.return_value = mock_data.get("funds")
    funds = broker.funds
    broker.fyers.funds.assert_called_once()
    assert funds == mock_data.get("funds")


def test_orders(mock_fyers):
    broker = mock_fyers
    broker.fyers.orderbook.return_value = mock_data.get("orders")
    orders = broker.orders
    broker.fyers.orderbook.assert_called_once()
    keys_in = [
        "order_id",
        "order_timestamp",
        "price",
        "quantity",
        "filled_quantity",
        "status",
        "exchange_order_id",
        "order_type",
    ]
    keys_not_in = [
        "id",
        "orderDateTime",
        "tradedPrice",
        "qty",
        "filledQty",
        "exchOrdId",
        "type",
    ]
    for order in orders:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in order
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in order


def test_orders_empty_orderbook(mock_fyers):
    broker = mock_fyers
    broker.fyers.orderbook.return_value = {}
    orders = broker.orders
    assert orders == [{}]


def test_orders_mappings(mock_fyers):
    # Test whether constants are matched correctly
    broker = mock_fyers
    broker.fyers.orderbook.return_value = mock_data.get("orders")
    orders = broker.orders
    assert orders[0]["status"] == "COMPLETE"
    assert orders[0]["exchange"] == "NSE"
    assert orders[0]["side"] == "buy"
    assert orders[0]["order_type"] == "MARKET"
    assert orders[1]["order_type"] == "LIMIT"
    assert orders[1]["side"] == "buy"
    assert orders[1]["status"] == "COMPLETE"
