from omspy.multi import *
from omspy.order import Order
from omspy.brokers.paper import Paper
import pytest
from unittest.mock import patch

class Paper2(Paper):
    pass

    def some_method(self):
        return 'method called'

@pytest.fixture
def users_simple():
    users = [
            User(broker=Paper()),
            User(broker=Paper(),scale=0.5,name='user2'),
            User(broker=Paper2(),scale=2)
            ]
    return users

def test_user_defaults():
    user = User(broker=Paper(),name='mine',
            scale=0.5)
    assert user.scale == 0.5
    assert user.name == 'mine'

def test_multi_user_defaults(users_simple):
    multi = MultiUser(users=users_simple)
    for user,expected in zip(multi.users,(1,0.5,2)):
        assert user.scale == expected
    multi.users[1].scale = 0.75
    assert multi.users[1].scale == 0.75
    assert multi.orders == {}

def test_multi_user_add(users_simple):
    multi = MultiUser(users=users_simple)
    multi.add(User(broker=Paper(), scale=1.5, name='added'))
    assert multi.users[-1].scale == 1.5
    assert multi.users[-1].name == 'added'
    assert multi.count == 4

def test_multi_user_order_place(users_simple):
    multi = MultiUser(users=users_simple)
    order = Order(symbol='aapl', side='buy', quantity=10)
    multi.order_place(order)
    orders = multi.orders.get(order.id)
    expected_qty = [10,5,20]
    for i in range(3):
        assert orders[i].quantity ==  expected_qty[i]
        assert orders[i].parent_id == order.id
        assert orders[i].id != order.id

def test_multi_user_order_place_broker(users_simple):
    multi = MultiUser(users=users_simple)
    with patch('omspy.brokers.paper.Paper') as order_place:
        for user in multi.users:
            # Patching  the order place method
            user.broker.order_place = order_place
    order = Order(symbol='aapl', side='buy', quantity=10)
    multi.order_place(order)
    assert order_place.call_count == 3



