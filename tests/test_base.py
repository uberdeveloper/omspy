import json
import pytest
from unittest.mock import patch, call
import pendulum
from copy import deepcopy
from omspy.base import Broker

# Load some mock data
with open("tests/data/kiteconnect/orders.json") as f:
    orders = json.load(f)
with open("tests/data/kiteconnect/trades.json") as f:
    trades = json.load(f)
with open("tests/data/kiteconnect/positions.json") as f:
    positions = json.load(f)


class Dummy(Broker):
    """
    Creating a dummy broker class to test base functions
    """

    def __init__(self):
        super(Dummy, self).__init__()

    def authenticate(self):
        return "Authentication done"

    def order_place(self, **kwargs):
        return kwargs

    def order_modify(self, order_id, **kwargs):
        return order_id

    def order_cancel(self, order_id):
        return order_id

    @property
    def orders(self):
        return orders

    @property
    def trades(self):
        return trades

    @property
    def positions(self):
        return positions


@pytest.fixture
def broker():
    return Dummy()


def test_dummy_broker_values(broker):
    assert broker.orders == orders
    assert broker.positions == positions
    assert broker.trades == trades
    assert broker.order_place(symbol="aapl") == {"symbol": "aapl"}
    assert broker.order_modify(1234) == 1234
    assert broker.order_cancel(1234) == 1234
