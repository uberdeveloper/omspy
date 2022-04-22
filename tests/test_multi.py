from omspy.multi import *
from omspy.order import Order, create_db
from omspy.brokers.paper import Paper
import pytest
from unittest.mock import patch
from copy import deepcopy


class Paper2(Paper):
    pass

    def some_method(self):
        return "method called"


@pytest.fixture
def users_simple():
    users = [
        User(broker=Paper()),
        User(broker=Paper(), scale=0.5, name="user2"),
        User(broker=Paper2(), scale=2),
    ]
    return users


@pytest.fixture
def simple_order():
    order = MultiOrder(
        symbol="amzn",
        quantity=10,
        side="buy",
        price=420,
        timezone="Europe/Paris",
        exchange="NASDAQ",
    )
    return order


def test_user_defaults():
    user = User(broker=Paper(), name="mine", scale=0.5)
    assert user.scale == 0.5
    assert user.name == "mine"


def test_multi_user_defaults(users_simple):
    multi = MultiUser(users=users_simple)
    for user, expected in zip(multi.users, (1, 0.5, 2)):
        assert user.scale == expected
    multi.users[1].scale = 0.75
    assert multi.users[1].scale == 0.75
    assert multi.orders == {}


def test_multi_user_add(users_simple):
    multi = MultiUser(users=users_simple)
    multi.add(User(broker=Paper(), scale=1.5, name="added"))
    assert multi.users[-1].scale == 1.5
    assert multi.users[-1].name == "added"
    assert multi.count == 4


def test_multi_user_order_place(users_simple):
    multi = MultiUser(users=users_simple)
    order = Order(symbol="aapl", side="buy", quantity=10)
    multi.order_place(order)
    orders = multi.orders.get(order.id)
    expected_qty = [10, 5, 20]
    for i in range(3):
        assert orders[i].quantity == expected_qty[i]
        assert orders[i].parent_id == order.id
        assert orders[i].id != order.id


def test_multi_user_order_place_broker(users_simple):
    multi = MultiUser(users=users_simple)
    with patch("omspy.brokers.paper.Paper") as order_place:
        for user in multi.users:
            # Patching  the order place method
            user.broker.order_place = order_place
    order = Order(symbol="aapl", side="buy", quantity=10)
    multi.order_place(order)
    assert order_place.call_count == 3


def test_multi_order_check_defaults(simple_order):
    order = simple_order
    assert order.symbol == "amzn"
    assert order.quantity == 10
    assert order.side == "buy"
    assert order.timezone == "Europe/Paris"
    assert order.exchange == "NASDAQ"
    assert order.orders == []
    assert order.count == 0


def test_multi_order_create(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.create(users=multi)
    assert order.count == 3
    for (order, expected) in zip(order.orders, (10, 5, 20)):
        assert order.order.quantity == expected


def test_multi_order_save_to_db(users_simple, simple_order):
    db = create_db()
    order = simple_order
    order.connection = db
    multi = MultiUser(users=users_simple)
    order.create(users=multi)
    assert db.execute("select count(*) from orders").fetchone()[0] == 4


def test_multi_order_execute(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    with patch("omspy.brokers.paper.Paper.order_place") as order_place:
        for user in multi.users:
            # Patching  the order place method
            user.broker.order_place = order_place
    order.execute(broker=multi)
    assert order_place.call_count == 3


def test_multi_order_execute_already_created(users_simple, simple_order):
    ur = UserOrder(order=simple_order, user=users_simple[0])
    with patch("omspy.multi.MultiOrder.create") as create:
        order = simple_order
        multi = MultiUser(users=MultiUser(users_simple[:1]))
        # Filling orders since create is a mock
        order.create(multi)
        # Caused a recursion error when directly assigned due to reference, copying the order fixed this
        order._orders = [deepcopy(ur)]
        order.execute(multi)


def test_multi_order_execute_dont_modify(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.create(multi)
    order.quantity = 100
    with patch("omspy.brokers.paper.Paper.order_place") as order_place:
        order.execute(multi)
        calls = order_place.call_args_list
        for c, expected in zip(calls, (10, 5, 20)):
            assert c.kwargs.get("quantity") == expected


def test_multi_order_create_clean_before_running_again(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.create(multi)
    assert order.count == 3
    order.quantity = 100
    order.create(multi)
    assert order.count == 3
    for (order, expected) in zip(order.orders, (100, 50, 200)):
        assert order.order.quantity == expected


def test_multi_order_modify(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.execute(multi)
    with patch("omspy.brokers.paper.Paper.order_modify") as order_modify:
        order.modify(quantity=50, price=400)
        assert order.quantity == 50
        assert order.price == 400
        for o in order.orders:
            print(o.order.price)
        call_args = order_modify.call_args_list
        assert order_modify.call_count == 3
        for o, a, q in zip(order.orders, call_args, (50, 25, 100)):
            assert o.order.quantity == q
            assert a.kwargs.get("quantity") == q
            assert a.kwargs.get("price") == 400


def test_multi_order_modify_no_quantity(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.execute(multi)
    with patch("omspy.brokers.paper.Paper.order_modify") as order_modify:
        order.modify(price=400, exchange="nfo")
        assert order.price == 400
        assert order.exchange == "nfo"
        for o in order.orders:
            print(o.order.price)
        call_args = order_modify.call_args_list
        assert order_modify.call_count == 3
        for o, a in zip(order.orders, call_args):
            assert a.kwargs.get("price") == 400


def test_multi_order_cancel(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.execute(multi)
    with patch("omspy.brokers.paper.Paper.order_cancel") as order_cancel:
        order.cancel()
        assert order_cancel.call_count == 3


def test_multi_order_defaults(simple_order):
    order = simple_order
    assert order.id is not None
    assert order.pseudo_id is not None
    assert order.timestamp is not None


def test_multi_order_pseudo_id(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.create(users=multi)
    for o in order.orders:
        assert order.pseudo_id == o.order.pseudo_id


def test_multi_order_is_multi_check(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.create(users=multi)
    for o in order.orders:
        assert o.order.is_multi is True


def test_multi_order_update(users_simple, simple_order):
    order = simple_order
    multi = MultiUser(users=users_simple)
    order.execute(multi)
    fake_ids = ["1111", "2222", "3333"]
    for (o, fi) in zip(order.orders, fake_ids):
        o.order.order_id = fi
    update = {
        "1111": {"filled_quantity": 3, "exchange_order_id": "aaaa"},
        "3333": {"filled_quantity": 16},
    }
    order.update(update)
    for o, qty in zip(order.orders, (3, 0, 16)):
        assert o.order.filled_quantity == qty
    assert order.orders[0].order.exchange_order_id == "aaaa"


def test_multi_order_update_save_db(users_simple, simple_order):

    db = create_db()
    order = simple_order
    order.connection = db
    multi = MultiUser(users=users_simple)
    order.execute(multi)
    fake_ids = ["1111", "2222", "3333"]
    for (o, fi) in zip(order.orders, fake_ids):
        o.order.order_id = fi
    update = {
        "1111": {"filled_quantity": 3, "exchange_order_id": "aaaa"},
        "3333": {"filled_quantity": 16},
    }
    order.update(update)
    filled = [0, 3, 0, 16]
    for i, row in enumerate(db.query("select * from orders order by timestamp")):
        assert row["filled_quantity"] == filled[i]
