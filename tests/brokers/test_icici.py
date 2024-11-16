import pytest
from omspy.brokers.icici import Icici
import json
from unittest.mock import patch, call
from copy import deepcopy


@pytest.fixture
def mock_icici():
    broker = Icici(
        "consumer_key", "consumer_secret", "mobilenumber", "password", "two_fa"
    )
    with patch("omspy.brokers.icici.BreezeConnect") as mock_broker:
        broker.breeze = mock_broker
        return broker


@pytest.fixture
def mock_data():
    # mock data for icici
    with open("tests/data/icici.json") as f:
        dct = json.load(f)
        return dct


def test_defaults():
    broker = Icici(
        "consumer_key",
        "consumer_secret",
        "mobilenumber",
        "password",
        "two_fa",
        "totp",
        "session_token",
    )
    assert broker.breeze is None


def test_authenticate():
    with patch("omspy.brokers.icici.BreezeConnect") as mock_broker:
        broker = Icici(
            "consumer_key",
            "consumer_secret",
            "mobilenumber",
            "password",
            "two_fa",
            "totp",
            "session_token",
        )
        broker.authenticate()
        mock_broker.return_value.generate_session.assert_called_once()


def test_orders(mock_icici, mock_data):
    mock_icici.breeze.get_order_list.side_effect = [mock_data["orders"]] * 4
    broker = mock_icici
    orders = broker.orders
    assert len(orders) == 4
    for key in (
        "order_id",
        "symbol",
        "side",
        "status",
        "average_price",
        "filled_quantity",
        "quantity",
        "price",
        "trigger_price",
        "order_type",
        "exchange_order_id",
        "timestamp",
        "last_price",
        "tag",
    ):
        for order in orders:
            assert key in order
        assert [order["quantity"] for order in orders] == [2, 2, 4, 20]
        assert [order["average_price"] for order in orders] == [
            1142,
            1130.3,
            672.45,
            154.31,
        ]
