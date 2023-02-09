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
def vorder_kwargs():
    return dict(
        order_id="20234567812",
        symbol="aapl",
        quantity=100,
        side="buy",
        exchange_timestamp=pendulum.datetime(2023, 1, 2, 7, 10),
    )


def test_vtrade_defaults(vtrade):
    assert vtrade.price == 120
    assert vtrade.side == "buy"


def test_vorder_defaults(vorder_kwargs):
    vorder = VOrder(**vorder_kwargs)
    assert vorder.quantity == 100
    assert vorder.side == "buy"
    assert vorder.status_message is None
    assert vorder.timestamp is not None
    assert vorder.filled_quantity == 0
    assert vorder.pending_quantity == 100
    assert vorder.canceled_quantity == 0


def test_vorder_quantities(vorder_kwargs):
    vorder_kwargs["pending_quantity"] = 50
    vorder = VOrder(**vorder_kwargs)
    assert vorder.quantity == 100
    assert vorder.filled_quantity == 50
    assert vorder.pending_quantity == 50
    assert vorder.canceled_quantity == 0

    vorder_kwargs["filled_quantity"] = 100
    vorder = VOrder(**vorder_kwargs)
    assert vorder.quantity == 100
    assert vorder.filled_quantity == 100
    assert vorder.pending_quantity == 0
    assert vorder.canceled_quantity == 0

    vorder_kwargs["canceled_quantity"] = 100
    vorder = VOrder(**vorder_kwargs)
    assert vorder.quantity == 100
    assert vorder.filled_quantity == 0
    assert vorder.pending_quantity == 0
    assert vorder.canceled_quantity == 100


def test_vposition_defaults():
    pos = VPosition(symbol="aapl")
    assert pos.buy_quantity == pos.sell_quantity == 0
    assert pos.buy_value == pos.sell_value == 0
