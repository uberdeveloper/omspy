from omspy.orders.peg import *
import pytest
from omspy.brokers.paper import Paper

def test_basic_peg():
    peg = BasicPeg(symbol='aapl', side='buy',
            quantity=100, broker = Paper())
    assert peg.count == 1
    assert peg.orders[0].order_type == 'LIMIT'
    assert peg.ltp['aapl'] == 0.0


