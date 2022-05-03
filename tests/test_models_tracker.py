import pytest
from omspy.models import *


@pytest.fixture
def simple():
    # A simple tracker
    tracker = Tracker(name="aapl")
    return tracker


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
