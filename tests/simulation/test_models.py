from omspy.simulation.models import *
import pendulum
import pytest


@pytest.fixture
def vtrade():
    return VTrade(
        trade_id="202310001",
        order_id="20234567812",
        symbol="aapl",
        quantity=50,
        price=120,
        side="buy",
        timestamp=pendulum.datetime(2023, 1, 2, 7, 10),
    )


@pytest.fixture
def vorder():
    return VOrder(
        order_id="20234567812",
        symbol="aapl",
        quantity=100,
        side="buy",
        exchange_timestamp=pendulum.datetime(2023, 1, 2, 7, 10),
    )


def test_vtrade_defaults(vtrade):
    assert vtrade.price == 120
    assert vtrade.side == "buy"


def test_vorder_defaults(vorder):
    assert vorder.quantity == 100
    assert vorder.side == "buy"
    assert vorder.status_message is None


def test_vposition_defaults():
    pos = VPosition(symbol="aapl")
    assert pos.buy_quantity == pos.sell_quantity == 0
    assert pos.buy_value == pos.sell_value == 0
