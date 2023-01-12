from omspy.simulation.virtual import *
import pytest
import random

random.seed(100)


def test_generate_price():
    assert generate_price() == 102
    assert generate_price(1000, 2000) == 1470
    assert generate_price(110, 100) == 107
