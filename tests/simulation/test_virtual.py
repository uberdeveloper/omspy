from omspy.simulation.virtual import *
import pytest
import random
from unittest.mock import patch
from pydantic import ValidationError

random.seed(100)


@pytest.fixture
def basic_ticker():
    return Ticker(name="aapl", token=1234, initial_price=125)


@pytest.fixture
def basic_broker():
    tickers = [
        Ticker(name="aapl", token=1111, initial_price=100),
        Ticker(name="goog", token=2222, initial_price=125),
        Ticker(name="amzn", token=3333, initial_price=260),
    ]
    return VirtualBroker(tickers=tickers)


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
        assert 50 <= b.quantity <= 150
    for a in ob.ask:
        assert 50 <= b.quantity <= 150


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
        assert 300 <= b.quantity <= 900
    for a in ob.ask:
        assert 300 <= b.quantity <= 900


def test_generate_orderbook_orders_count():
    with patch("random.randrange") as randrange:
        randrange.side_effect = [10, 10, 100, 100] * 20
        ob = generate_orderbook()
    for a, b in zip(ob.ask, ob.bid):
        assert a.orders_count <= a.quantity
        assert b.orders_count <= b.quantity


def test_ticker_defaults():
    ticker = Ticker(name="abcd")
    assert ticker.name == "abcd"
    assert ticker.token is None
    assert ticker.initial_price == 100
    assert ticker.mode == TickerMode.RANDOM


def test_ticker_changed(basic_ticker):
    ticker = basic_ticker
    assert ticker.name == "aapl"
    assert ticker.token == 1234
    assert ticker.initial_price == 125
    assert ticker.mode == TickerMode.RANDOM
    assert ticker._high == ticker._low == ticker._ltp == 125


def test_ticker_is_random():
    ticker = Ticker(name="abcd")
    assert ticker.is_random is True
    ticker.mode = TickerMode.MANUAL
    assert ticker.is_random is False


def test_ticker_ltp(basic_ticker):
    ticker = basic_ticker
    for i in range(15):
        ticker.ltp
    assert ticker._ltp == 120
    assert ticker._high == 125
    assert ticker._low == 116.95


def test_ticker_ohlc(basic_ticker):
    ticker = basic_ticker
    ticker.ohlc() == dict(open=125, high=125, low=125, close=125)
    for i in range(15):
        ticker.ltp
    ticker.ohlc() == dict(open=125, high=125, low=116.95, close=120)


def test_virtual_broker_defaults(basic_broker):
    b = basic_broker
    assert b.name == "VBroker"
    assert len(b.tickers) == 3
    assert b.failure_rate == 0.001


def test_virtual_broker_is_failure(basic_broker):
    b = basic_broker
    assert b.is_failure is False
    b.failure_rate = 1.0  # everything should fail now
    assert b.is_failure is True
    with pytest.raises(ValidationError):
        b.failure_rate = -1
    with pytest.raises(ValidationError):
        b.failure_rate = 2
