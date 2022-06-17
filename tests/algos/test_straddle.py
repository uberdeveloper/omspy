import pytest
from omspy.algos.straddle import *
from pydantic import ValidationError


@pytest.fixture
def simple_straddle():
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        return ShortStraddle(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
            symbols=("nifty22may17500ce", "nifty22may17500pe"),
        )


@pytest.fixture
def price_straddle():
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        return ShortStraddle(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
            symbols=("nifty22may17500ce", "nifty22may17500pe"),
            limit_price=(200, 210.4),
            trigger_price=(240, 268),
            stop_price=(242, 270),
        )


def test_base_strategy_defaults():
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        base = BaseStrategy(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
        )
        assert base.timer.start_time == pendulum.datetime(2022, 1, 1, 10, 10)
        assert base.timer.end_time == pendulum.datetime(2022, 1, 1, 15, 10)
        assert base._pegs == []


def test_base_strategy_end_time_less_than_start_time():
    with pytest.raises(ValidationError):
        base = BaseStrategy(
            start_time=pendulum.datetime(2022, 1, 2, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
        )


def test_base_strategy_start_time_less_than_now():
    known = pendulum.datetime(2022, 1, 4, 10, 15)
    with pendulum.test(known):
        with pytest.raises(ValidationError):
            base = BaseStrategy(
                start_time=pendulum.datetime(2022, 1, 4, 10, 12),
                end_time=pendulum.datetime(2022, 1, 4, 10, 20),
            )


def test_base_strategy_time():
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        base = BaseStrategy(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
            timezone="Europe/Paris",
        )
        assert base.timer.start_time == base.start_time
        assert base.timer.end_time == base.end_time


def test_short_straddle_defaults(simple_straddle):
    assert simple_straddle.start_time == pendulum.datetime(2022, 1, 1, 10, 10)
    assert simple_straddle.symbols == ("nifty22may17500ce", "nifty22may17500pe")
    assert simple_straddle.order is not None
    assert list(simple_straddle._order_map.keys()) == [
        "entry1",
        "exit1",
        "entry2",
        "exit2",
    ]
    assert simple_straddle._pegs == []


def test_short_straddle_create_order_defaults(simple_straddle):
    straddle = simple_straddle
    assert straddle.order.count == 0
    straddle.create_order()
    assert straddle.order.count == 4
    assert [x.side for x in straddle.order.orders] == ["sell", "sell", "buy", "buy"]
    assert [x.order_type for x in straddle.order.orders] == [
        "MARKET",
        "MARKET",
        "SL",
        "SL",
    ]


def test_short_straddle_limit_prices(price_straddle):
    straddle = price_straddle
    order = straddle.create_order()
    assert order.orders[0].price == 200
    assert order.orders[1].price == 210.4
    assert order.orders[2].trigger_price == 240
    assert order.orders[3].trigger_price == 268
    assert order.orders[2].price == 242
    assert order.orders[3].price == 270
