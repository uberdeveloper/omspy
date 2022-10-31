from omspy.orders.depth import *
from omspy.models import *
import pytest


@pytest.fixture
def simple_depth():
    return MarketDepth(
        bids=[
            Quote(price=100, quantity=54, orders_count=4),
            Quote(price=99, quantity=1254, orders_count=12),
            Quote(price=98, quantity=154, orders_count=4),
        ],
        asks=[
            Quote(price=101, quantity=99, orders_count=4),
            Quote(price=102, quantity=1288, orders_count=61),
            Quote(price=103, quantity=359, orders_count=7),
        ],
    )


def test_market_depth_defaults(simple_depth):
    assert simple_depth.bids[0].price == 100
    assert simple_depth.asks[0].price == 101
    assert simple_depth.tick == 0.05


def test_market_depth_midpoint(simple_depth):
    assert simple_depth.midpoint == 100.5
    simple_depth.tick = 0.07
    assert simple_depth.midpoint == 100.52


def test_market_depth_bid(simple_depth):
    assert simple_depth.bid() == 100
    assert simple_depth.bid(2) == 98
    assert simple_depth.bid(-1) == 98


def test_market_depth_ask(simple_depth):
    assert simple_depth.ask() == 101
    assert simple_depth.ask(1) == 102
    assert simple_depth.ask(-1) == 103


def test_market_depth_sort(simple_depth):
    simple_depth.bids.append(Quote(price=100.5, quantity=7))
    simple_depth.asks.append(Quote(price=101.7, quantity=21))
    assert simple_depth.bid(-1) == 100.5
    assert simple_depth.bid(0) == 100
    assert simple_depth.ask(-1) == 101.7
    assert simple_depth.midpoint == 100.5
    simple_depth.sort()
    print(simple_depth.bids)
    assert simple_depth.bid() == 100.5
    assert simple_depth.bid(-1) == 98
    assert simple_depth.ask(1) == 101.7
    assert simple_depth.midpoint == 100.75
