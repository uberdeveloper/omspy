from omspy.order import OrderStrategy, create_db
import pendulum
import pytest
from unittest.mock import patch


@pytest.fixture
def new_db():
    return create_db()


@pytest.fixture
def simple():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(100000, 100100)
        strategy = OrderStrategy(broker=broker)
        return strategy


def test_order_strategy_defaults(simple):
    s = simple
    assert s.orders == []
