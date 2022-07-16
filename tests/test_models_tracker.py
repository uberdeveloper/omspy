import pytest
from omspy.models import *
from pydantic import ValidationError


@pytest.fixture
def simple():
    # A simple tracker
    tracker = Tracker(name="aapl")
    return tracker


@pytest.fixture
def simple_timer():
    with pendulum.test(pendulum.datetime(2022, 4, 1)):
        return Timer(
            start_time=pendulum.datetime(2022, 4, 1, 9, 20),
            end_time=pendulum.datetime(2022, 4, 1, 15, 20),
        )


@pytest.fixture
def time_tracker():
    with pendulum.test(pendulum.datetime(2022, 4, 1)):
        return TimeTracker(
            name="tracker",
            start_time=pendulum.datetime(2022, 4, 1, 9, 20),
            end_time=pendulum.datetime(2022, 4, 1, 15, 20),
        )


def test_tracker_defaults(simple):
    tracker = simple
    assert tracker.name == "aapl"


def test_tracker_update(simple):
    tracker = simple
    tracker.last_price = 200
    assert tracker.last_price == 200
    assert tracker.high == -1e100
    assert tracker.low == 1e100
    tracker.update(203)
    assert tracker.high == tracker.low == 203
    tracker.update(201)
    assert tracker.low == 201
    assert tracker.high == 203
    tracker.update(202)
    assert tracker.low == 201
    assert tracker.high == 203
    tracker.update(203.5)
    assert tracker.high == 203.5


def test_timer_end_time_less_than_start_time():
    with pytest.raises(ValidationError):
        base = Timer(
            start_time=pendulum.datetime(2022, 1, 2, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
        )


def test_timer_start_time_less_than_now():
    known = pendulum.datetime(2022, 1, 4, 10, 15)
    with pendulum.test(known):
        with pytest.raises(ValidationError):
            base = Timer(
                start_time=pendulum.datetime(2022, 1, 4, 10, 12),
                end_time=pendulum.datetime(2022, 1, 4, 10, 20),
            )


def test_timer_has_started(simple_timer):
    timer = simple_timer
    known = pendulum.datetime(2022, 4, 1, 9, 15)
    with pendulum.test(known):
        assert timer.has_started is False
    with pendulum.test(known.add(minutes=6)):
        assert timer.has_started is True


def test_timer_has_completed(simple_timer):
    timer = simple_timer
    known = pendulum.datetime(2022, 4, 1, 9, 25)
    with pendulum.test(known):
        assert timer.has_started is True
        assert timer.has_completed is False
    with pendulum.test(known.add(hours=6)):
        assert timer.has_completed is True


def test_time_tracker_inherit(time_tracker):
    tracker = time_tracker
    assert tracker.name == "tracker"
    assert tracker.start_time == pendulum.datetime(2022, 4, 1, 9, 20)
    assert tracker.end_time == pendulum.datetime(2022, 4, 1, 15, 20)
    assert tracker.has_started is True
    # TODO: Tracker to update only after start
    for ltps in (201, 207, 199, 224, 208, 203, 216):
        tracker.update(ltps)
    assert tracker.last_price == 216
    assert tracker.high == 224
    assert tracker.low == 199


def test_timer_is_running(time_tracker):
    tracker = time_tracker
    known = pendulum.datetime(2022, 4, 1)
    with pendulum.test(known):
        assert tracker.is_running is False
    with pendulum.test(known.add(minutes=600)):
        assert tracker.is_running is True
    with pendulum.test(known.add(minutes=920)):
        assert tracker.is_running is True
    with pendulum.test(known.add(minutes=921)):
        assert tracker.is_running is False
