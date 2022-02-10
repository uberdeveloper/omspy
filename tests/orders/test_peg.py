from omspy.orders.peg import *
import pytest
from omspy.brokers.paper import Paper
import pendulum


def test_basic_peg():
    peg = BasicPeg(symbol="aapl", side="buy", quantity=100, broker=Paper())
    assert peg.count == 1
    assert peg.orders[0].order_type == "LIMIT"
    assert peg.ltp["aapl"] == 0.0


def test_peg_market_defaults():
    known = pendulum.datetime(2022, 1, 1, 10)
    with pendulum.test(known):
        peg = PegMarket(symbol="aapl", side="buy", quantity=100, broker=Paper())
        assert peg.num_pegs == 0
        assert peg._max_pegs == 6
        assert peg._expire_at == pendulum.datetime(2022, 1, 1, 10, minute=1)
        assert peg.next_peg == pendulum.datetime(2022, 1, 1, 10, second=10)


def test_peg_market_change_defaults():
    known = pendulum.datetime(2022, 1, 1, 10, 5, 45, tz="Asia/Kolkata")
    with pendulum.test(known):
        peg = PegMarket(
            symbol="aapl",
            side="buy",
            quantity=100,
            broker=Paper(),
            duration=150,
            peg_every=20,
            timezone="Asia/Kolkata",
        )
        assert peg.num_pegs == 0
        assert peg._max_pegs == 7
        assert peg._expire_at == pendulum.datetime(
            2022, 1, 1, 10, minute=8, second=15, tz="Asia/Kolkata"
        )
        assert peg.next_peg == pendulum.datetime(
            2022, 1, 1, 10, minute=6, second=5, tz="Asia/Kolkata"
        )
