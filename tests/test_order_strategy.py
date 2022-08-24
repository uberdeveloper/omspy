from omspy.order import Order, CompoundOrder, OrderStrategy, create_db
import pendulum
import pytest
from unittest.mock import patch
from collections import Counter


@pytest.fixture
def new_db():
    return create_db()


@pytest.fixture
def simple():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(100000, 100100)
        strategy = OrderStrategy(broker=broker)
        return strategy


@pytest.fixture
def strategy(simple):
    symbols = ["aapl", "goog", "dow", "amzn"]
    prices = [100, 102, 105, 110]
    quantities = [10, 20, 30, 40]
    orders = []
    for s, p, q in zip(symbols, prices, quantities):
        order = Order(symbol=s, quantity=q, price=p, side="buy")
        order.average_price = p
        order.filled_quantity = q
        orders.append(order)
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(100000, 100100)
        com1 = CompoundOrder(broker=broker)
        com1.add(orders[0])
        com1.add(orders[1])
        com2 = CompoundOrder(broker=broker)
        com2.add(orders[2])
        com2.add(orders[3])
        strategy = OrderStrategy(broker=broker, orders=[com1, com2])
        return strategy


def test_order_strategy_defaults(simple):
    s = simple
    assert s.orders == []


def test_order_strategy_counter(strategy):
    s = strategy
    assert s.positions == Counter(dict(aapl=10, goog=20, amzn=40, dow=30))
