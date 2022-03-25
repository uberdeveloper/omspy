from omspy.orders.depth import *
from omspy.models import *
import pytest


@pytest.fixture
def simple_depth():
    return MarketDepth(
        bids=[Quote(price=100, quantity=12, orders=4)],
        asks=[Quote(price=101, quantity=12, orders=4)],
    )


def test_market_depth_defaults(simple_depth):
    assert simple_depth.bids[0].price == 100
    assert simple_depth.asks[0].price == 101
    assert simple_depth.tick == 0.05


def test_market_depth_midpoint(simple_depth):
    assert simple_depth.midpoint == 100.5
    simple_depth.tick = 0.07
    assert simple_depth.midpoint == 100.52
