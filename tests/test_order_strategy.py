from omspy.order import Order, CompoundOrder, OrderStrategy, create_db
import pendulum
import pytest
from unittest.mock import patch
from collections import Counter
from omspy.brokers.zerodha import Zerodha


class CompoundOrderNoRun(CompoundOrder):
    d = 0

    # This should not be called by order strategy run
    @property
    def run(self):
        self.d = 100


class CompoundOrderRun(CompoundOrder):
    d = 0

    def run(self, data):
        self.d = data.get("xom")


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
        order.filled_quantity = q - 1
        orders.append(order)
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(100000, 100100)
        com1 = CompoundOrder(broker=broker)
        com1.add(orders[0])
        com1.add(orders[1])
        com1.execute_all()
        com2 = CompoundOrder(broker=broker)
        com2.add(orders[2])
        com2.add(orders[3])
        com2.execute_all()
        strategy = OrderStrategy(broker=broker, orders=[com1, com2])
        return strategy


def test_order_strategy_defaults(simple):
    s = simple
    assert s.orders == []


def test_order_strategy_positions(strategy):
    s = strategy
    assert s.positions == Counter(dict(aapl=9, goog=19, amzn=39, dow=29))


def test_order_strategy_update_ltp(strategy):
    s = strategy
    assert s.ltp == {}
    s.update_ltp(dict(aapl=120))
    assert s.ltp == dict(aapl=120)
    s.update_ltp(dict(goog=100, amzn=110))
    assert s.ltp == dict(aapl=120, goog=100, amzn=110)


def test_order_strategy_update_orders(strategy):
    s = strategy
    assert s.orders[0].orders[0].exchange_order_id is None
    s.update_orders(
        {"100000": {"exchange_order_id": 11111}, "100003": {"exchange_order_id": 11112}}
    )
    assert s.orders[0].orders[0].exchange_order_id == 11111
    assert s.orders[1].orders[1].exchange_order_id == 11112


def test_order_strategy_mtm(strategy):
    s = strategy
    s.update_ltp(dict(goog=100, amzn=110, dow=105))
    print(s.mtm)
    for o in s.orders:
        print(o.mtm)
    assert s.mtm == {
        "goog": 19 * (100 - 102),
        "amzn": 29 * (110 - 110),
        "dow": 0,
        "aapl": -900,
    }


def test_order_strategy_run(strategy):
    s = strategy
    com = CompoundOrderRun(broker=strategy.broker)
    com.add(Order(symbol="xom", quantity=100, side="buy"))
    com2 = CompoundOrderNoRun(broker=strategy.broker)
    com2.add(Order(symbol="xom", quantity=100, side="buy"))
    s.orders.append(com)
    s.orders.append(com2)
    s.run(dict(goog=100, amzn=110, xom=105))
    assert s.orders[-2].d == 105
    # TODO: assert s.orders[-1].d == 0


def test_order_strategy_add(strategy):
    s = strategy
    assert len(s.orders) == 2
    com = CompoundOrderRun(broker=strategy.broker)
    com.add(Order(symbol="xom", quantity=100, side="buy"))
    s.orders.append(com)
    assert len(s.orders) == 3
