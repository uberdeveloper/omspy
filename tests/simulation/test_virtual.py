from omspy.simulation.virtual import *
import pytest
import random

random.seed(100)


def test_generate_price():
    assert generate_price() == 102
    assert generate_price(1000, 2000) == 1470
    assert generate_price(110, 100) == 107


def test_generate_orderbook_default():
    ob = generate_orderbook()
    ob.bid[-1].price == 99.96
    ob.ask[-1].price == 100.04
    for b in ob.bid:
        assert 50 < b.quantity < 150
    for a in ob.ask:
        assert 50 < b.quantity < 150


def test_generate_orderbook_swap_bid_ask():
    ob = generate_orderbook(bid=100.05, ask=100)
    ob.bid[-1].price == 99.96
    ob.ask[-1].price == 100.04
    for b in ob.bid:
        assert 50 < b.quantity < 150
    for a in ob.ask:
        assert 50 < b.quantity < 150


def test_generate_orderbook_depth():
    ob = generate_orderbook(depth=100)
    ob.bid[-1].price == 99.01
    ob.ask[-1].price == 100.99
    assert len(ob.bid) == 100
    assert len(ob.ask) == 100


def test_generate_orderbook_price_and_tick_and_quantity():
    ob = generate_orderbook(bid=1000, ask=1005, tick=2, depth=10, quantity=600)
    ob.bid[-1].price == 982
    ob.ask[-1].price == 1023
    assert len(ob.bid) == len(ob.ask) == 10
    for b in ob.bid:
        assert 300 < b.quantity < 900
    for a in ob.ask:
        assert 300 < b.quantity < 900
