from omspy.brokers.zerodha import Zerodha
from unittest.mock import patch, call
import pytest
import json
from copy import deepcopy


@pytest.fixture
def mock_kite():
    broker = Zerodha("api_key", "secret", "user_id", "password", "pin")
    with patch("kiteconnect.KiteConnect") as mock:
        broker.kite = mock
    return broker


def test_profile(mock_kite):
    broker = mock_kite
    with open("tests/data/kiteconnect/profile.json") as f:
        mock_data = json.load(f)
    broker.kite.profile.return_value = mock_data
    profile = broker.profile
    broker.kite.profile.assert_called_once()
    assert profile == mock_data


def test_orders(mock_kite):
    broker = mock_kite
    with open("tests/data/kiteconnect/orders.json") as f:
        mock_data = json.load(f)
    broker.kite.orders.return_value = mock_data
    orders = broker.orders
    broker.kite.orders.assert_called_once()
    keys_in = [
        "side",
        "symbol",
        "order_id",
        "order_timestamp",
        "price",
        "quantity",
        "filled_quantity",
        "status",
        "exchange_order_id",
        "order_type",
    ]
    keys_not_in = ["transaction_type", "tradingsymbol"]
    for order in orders:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in order
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in order


def test_orders_empty_orderbook(mock_kite):
    broker = mock_kite
    broker.kite.orders.return_value = {}
    orders = broker.orders
    assert orders == [{}]


def test_trades(mock_kite):
    broker = mock_kite
    with open("tests/data/kiteconnect/trades.json") as f:
        mock_data = json.load(f)
    broker.kite.trades.return_value = mock_data
    trades = broker.trades
    broker.kite.trades.assert_called_once()
    keys_in = ["trade_id", "symbol"]
    keys_not_in = ["tradingsymbol"]
    for trade in trades:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in trade
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in trade


def test_positions(mock_kite):
    broker = mock_kite
    with open("tests/data/kiteconnect/positions.json") as f:
        mock_data = json.load(f)
    broker.kite.positions.return_value = mock_data
    positions = broker.positions
    broker.kite.positions.assert_called_once()
    keys_in = ["symbol"]
    keys_not_in = ["tradingsymbol"]
    for position in positions:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in position
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in position


def test_positions_side(mock_kite):
    broker = mock_kite
    with open("tests/data/kiteconnect/positions.json") as f:
        mock_data = json.load(f)
    broker.kite.positions.return_value = mock_data
    positions = broker.positions
    assert positions[0]["side"] == "SELL"
    assert positions[1]["side"] == "BUY"
    assert positions[2]["side"] == "SELL"
