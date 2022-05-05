import pytest
from omspy.algos.straddle import *
from pydantic import ValidationError

@pytest.fixture
def simple_straddle():
    known = pendulum.datetime(2022,1,1)
    with pendulum.test(known):
        return ShortStraddle(
                start_time=pendulum.datetime(2022, 1, 1, 10, 10),
                end_time=pendulum.datetime(2022, 1, 1, 15, 10),
                symbols=('nifty22may17500ce', 'nifty22may17500pe'),
                stop = (30,30)
                )

def test_base_strategy_defaults():
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        base = BaseStrategy(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
        )


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
    assert simple_straddle.start_time == pendulum.datetime(2022,1,1,10,10)
    assert simple_straddle.symbols == ('nifty22may17500ce', 'nifty22may17500pe')

def test_short_straddle_create_order_defaults(simple_straddle):
    straddle = simple_straddle
    assert straddle.order.count == 0
    straddle.create_order()
    assert straddle.order.count == 4
    assert [x.side for x in straddle.order.orders] == ['sell', 'sell', 'buy', 'buy']

