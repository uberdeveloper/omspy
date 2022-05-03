import pytest
from omspy.algos.straddle import *
from pydantic import ValidationError


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
