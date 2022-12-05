import pytest
from unittest.mock import patch, call
from omspy.order import *
from omspy.brokers.paper import Paper
from collections import Counter
import pendulum
from copy import deepcopy
import sqlite3
import json
from sqlite_utils import Database
from omspy.models import OrderLock


@pytest.fixture
def new_db():
    return create_db()


@pytest.fixture
def simple_order():
    return Order(
        symbol="aapl",
        side="buy",
        quantity=10,
        order_type="LIMIT",
        price=650,
        order_id="abcdef",
    )


@pytest.fixture
def order_kwargs():
    # Order response for the simple order
    return dict(
        quantity=10,
        price=650,
        trigger_price=0,
        order_type="LIMIT",
        disclosed_quantity=0,
        symbol="AAPL",
        side="BUY",
    )


@pytest.fixture
def paper2():
    """
    Broker with attributes added
    """

    class Paper2:
        @property
        def attribs_to_copy_execute(self):
            return ("exchange", "client_id")

        def attribs_to_copy_modify(self):
            return ("exchange",)

        def attribs_to_copy_cancel(self):
            return "client_id"

    return Paper2()


@pytest.fixture
def compound_order():
    con = create_db()
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(100000, 100010)
        com = CompoundOrder(broker=broker, connection=con)
        com.add_order(symbol="aapl", quantity=20, side="buy")
        com.add_order(symbol="goog", quantity=10, side="sell", average_price=338)
        com.add_order(symbol="aapl", quantity=12, side="sell", average_price=975)
        return com


@pytest.fixture
def simple_compound_order():
    con = create_db()
    com = CompoundOrder(broker=Paper(), connection=con)
    com.add_order(
        symbol="aapl",
        quantity=20,
        side="buy",
        filled_quantity=20,
        average_price=920,
        status="COMPLETE",
        order_id="aaaaaa",
    )
    com.add_order(
        symbol="goog",
        quantity=10,
        side="sell",
        filled_quantity=10,
        average_price=338,
        status="COMPLETE",
        order_id="bbbbbb",
    )
    com.add_order(
        symbol="aapl",
        quantity=12,
        side="sell",
        filled_quantity=9,
        average_price=975,
        order_id="cccccc",
    )
    return com


@pytest.fixture
def compound_order_average_prices():
    com = CompoundOrder(broker=Paper())
    com.add_order(
        symbol="aapl",
        quantity=20,
        side="buy",
        order_id="111111",
        filled_quantity=20,
        average_price=1000,
    )
    com.add_order(
        symbol="aapl",
        quantity=20,
        side="buy",
        order_id="222222",
        filled_quantity=20,
        average_price=900,
    )
    com.add_order(
        symbol="goog",
        quantity=20,
        side="sell",
        order_id="333333",
        filled_quantity=20,
        average_price=700,
    )
    com.add_order(
        symbol="goog",
        quantity=15,
        side="sell",
        order_id="444444",
        filled_quantity=15,
        average_price=600,
    )
    return com


def test_order_simple():
    order = Order(symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris")
    assert order.quantity == 10
    assert order.pending_quantity == 10
    assert order.filled_quantity == 0
    assert order.timestamp is not None
    assert order.id is not None
    assert order.timezone == "Europe/Paris"
    assert order.lock == OrderLock()
    assert order._frozen_attrs == {"symbol", "side"}


def test_order_id_custom():
    order = Order(symbol="aapl", side="buy", quantity=10, id="some_hex_digit")
    assert order.id == "some_hex_digit"


def test_order_is_complete():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.is_complete is False
    order.filled_quantity = 10
    assert order.is_complete is True


def test_order_is_complete_other_cases():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.filled_quantity = 6
    assert order.is_complete is False
    order.cancelled_quantity = 4
    assert order.is_complete is True


def test_order_is_pending():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.is_pending is True
    order.filled_quantity = 10
    assert order.is_pending is False
    order.filled_quantity, order.cancelled_quantity = 5, 5
    assert order.is_pending is False
    order.filled_quantity, order.cancelled_quantity = 5, 4
    assert order.is_pending is True
    order.status = "COMPLETE"
    assert order.is_pending is False


@pytest.mark.parametrize(
    "test_input,expected",
    [((15134,), 15100), ((15134, 0, 50), 15150), ((15176, 0, 50), 15200)],
)
def test_get_option(test_input, expected):
    assert get_option(*test_input) == expected


def test_order_update_simple():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.update(
        {"filled_quantity": 7, "average_price": 912, "exchange_order_id": "abcd"}
    )
    assert order.filled_quantity == 7
    assert order.average_price == 912
    assert order.exchange_order_id == "abcd"


def test_order_update_timestamp():
    known = pendulum.datetime(2021, 1, 1, 12, tz="Europe/Paris")
    with pendulum.test(known):
        order = Order(symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris")
    assert order.timestamp == known
    with pendulum.test(known.add(minutes=5)):
        order.update(
            {"filled_quantity": 7, "average_price": 912, "exchange_order_id": "abcd"}
        )
        assert order.last_updated_at == known.add(minutes=5)
        diff = order.last_updated_at - order.timestamp
        assert diff.in_seconds() == 300
        print(order.timestamp, known)
        assert order.timestamp == known


def test_order_update_non_attribute():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.update(
        {"filled_quantity": 7, "average_price": 912, "message": "not in attributes"}
    )
    assert order.filled_quantity == 7
    assert hasattr(order, "message") is False


def test_order_update_do_not_update_when_complete():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.filled_quantity = 7
    assert order.average_price == 0
    order.update({"average_price": 920})
    assert order.average_price == 920
    order.status = "COMPLETE"
    order.update({"average_price": 912, "quantity": 10})
    # Should not update since order is marked COMPLETE
    assert order.average_price == 920
    assert order.filled_quantity == 7
    # We can still change the attribute directly
    order.filled_quantity = 10
    assert order.filled_quantity == 10


def test_order_update_do_not_update_rejected_order():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.filled_quantity = 7
    order.average_price = 912
    order.status = "REJECTED"
    order.update({"average_price": 920})
    assert order.average_price == 912


def test_order_update_do_not_update_cancelled_order():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.filled_quantity = 7
    order.average_price = 912
    order.status = "CANCELED"
    order.update({"average_price": 920})
    assert order.average_price == 912
    order.status = "CANCELLED"
    order.update({"average_price": 920})
    assert order.average_price == 912
    order.status = "OPEN"
    order.update({"average_price": 920})
    assert order.average_price == 920


def test_order_update_do_not_update_timestamp_for_completed_orders():
    known = pendulum.datetime(2022, 11, 5, tz="local")
    with pendulum.test(known):
        order = Order(symbol="aapl", side="buy", quantity=10)
    for i in (10, 20, 30, 40):
        with pendulum.test(known.add(seconds=i)):
            order.update({"filled_quantity": 10})
            assert order.last_updated_at == known.add(seconds=10)

    # Test with a rejected order
    with pendulum.test(known):
        order = Order(symbol="aapl", side="buy", quantity=10)
    for i in (10, 20, 30, 40):
        with pendulum.test(known.add(seconds=i)):
            order.update({"filled_quantity": 5})
            order.status = "REJECTED"
            assert order.last_updated_at == known.add(seconds=10)


def test_compound_order_id_custom():
    order = CompoundOrder(broker=Paper(), id="some_id")
    order.add_order(symbol="aapl", quantity=5, side="buy", filled_quantity=5)
    assert order.id == "some_id"
    assert order.orders[0].parent_id == "some_id"


def test_compound_order_count(simple_compound_order):
    order = simple_compound_order
    assert order.count == 3


def test_compound_order_positions(simple_compound_order):
    order = simple_compound_order
    assert order.positions == Counter({"aapl": 11, "goog": -10})
    order.add_order(symbol="boe", side="buy", quantity=5, filled_quantity=5)
    assert order.positions == Counter({"aapl": 11, "goog": -10, "boe": 5})


def test_compound_order_add_order():
    order = CompoundOrder(broker=Paper())
    order.add_order(symbol="aapl", quantity=5, side="buy", filled_quantity=5)
    order.add_order(symbol="aapl", quantity=4, side="buy", filled_quantity=4)
    assert order.count == 2
    assert order.positions == Counter({"aapl": 9})


def test_compound_order_average_buy_price(compound_order_average_prices):
    order = compound_order_average_prices
    assert order.average_buy_price == dict(aapl=950)


def test_compound_order_average_sell_price(compound_order_average_prices):
    order = compound_order_average_prices
    # Rounding to match significane
    dct = order.average_sell_price
    for k, v in dct.items():
        dct[k] = round(v, 2)
    assert dct == dict(goog=657.14)


def test_compound_order_update_orders(simple_compound_order):
    order = simple_compound_order
    order_data = {
        "aaaaaa": {
            "order_id": "aaaaaa",
            "exchange_order_id": "hexstring",
            "price": 134,
            "average_price": 134,
        },
        "cccccc": {
            "order_id": "cccccc",
            "filled_quantity": 12,
            "status": "COMPLETE",
            "average_price": 180,
            "exchange_order_id": "some_exchange_id",
        },
    }
    updates = order.update_orders(order_data)
    assert updates == {"cccccc": True}
    assert order.orders[-1].filled_quantity == 12
    assert order.orders[-1].status == "COMPLETE"
    assert order.orders[-1].average_price == 180
    assert order.orders[-1].exchange_order_id == "some_exchange_id"


def test_compound_order_buy_quantity(simple_compound_order):
    order = simple_compound_order
    assert order.buy_quantity == {"aapl": 20}


def test_compound_order_sell_quantity(simple_compound_order):
    order = simple_compound_order
    assert order.sell_quantity == {"goog": 10, "aapl": 9}


def test_compound_order_update_ltp(simple_compound_order):
    order = simple_compound_order
    assert order.ltp == {}
    assert order.update_ltp({"amzn": 300, "goog": 350}) == {"amzn": 300, "goog": 350}
    order.update_ltp({"aapl": 600})
    assert order.ltp == {"amzn": 300, "goog": 350, "aapl": 600}
    assert order.update_ltp({"goog": 365}) == {"amzn": 300, "goog": 365, "aapl": 600}


def test_compound_order_net_value(simple_compound_order, compound_order_average_prices):
    order = simple_compound_order
    order2 = compound_order_average_prices
    order.orders.extend(order2.orders)
    assert order.net_value == Counter({"aapl": 47625, "goog": -26380})


def test_compound_order_mtm(simple_compound_order):
    order = simple_compound_order
    order.update_ltp({"aapl": 900, "goog": 300})
    assert order.mtm == {"aapl": 275, "goog": 380}
    order.update_ltp({"aapl": 885, "goog": 350})
    assert order.mtm == {"aapl": 110, "goog": -120}


def test_compound_order_total_mtm(simple_compound_order):
    order = simple_compound_order
    order.update_ltp({"aapl": 900, "goog": 300})
    assert order.total_mtm == 655
    order.update_ltp({"aapl": 885, "goog": 350})
    assert order.total_mtm == -10


def test_simple_order_execute():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650
        )
        order.execute(broker=broker)
        broker.order_place.assert_called_once()
        kwargs = dict(
            symbol="AAPL",
            side="BUY",
            quantity=10,
            order_type="LIMIT",
            price=650,
            trigger_price=0.0,
            disclosed_quantity=0,
        )
        assert broker.order_place.call_args_list[0] == call(**kwargs)


def test_simple_order_execute_kwargs():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650
        )
        order.execute(broker=broker, exchange="NSE", variety="regular")
        broker.order_place.assert_called_once()
        kwargs = dict(
            symbol="AAPL",
            side="BUY",
            quantity=10,
            order_type="LIMIT",
            price=650,
            trigger_price=0.0,
            disclosed_quantity=0,
            exchange="NSE",
            variety="regular",
        )
        assert broker.order_place.call_args_list[0] == call(**kwargs)


def test_simple_order_execute_do_not_update_existing_kwargs():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650
        )
        order.execute(
            broker=broker,
            exchange="NSE",
            variety="regular",
            quantity=20,
            order_type="MARKET",
        )
        broker.order_place.assert_called_once()
        kwargs = dict(
            symbol="AAPL",
            side="BUY",
            quantity=10,
            order_type="LIMIT",
            price=650,
            trigger_price=0.0,
            disclosed_quantity=0,
            exchange="NSE",
            variety="regular",
        )


def test_simple_order_modify(simple_order):
    order = simple_order
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.price = 630
        order.modify(broker=broker)
        broker.order_modify.assert_called_once()
        kwargs = dict(
            order_id="abcdef",
            quantity=10,
            order_type="LIMIT",
            price=630,
            trigger_price=0.0,
            disclosed_quantity=0,
        )
        assert broker.order_modify.call_args_list[0] == call(**kwargs)


def test_simple_order_cancel():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            order_id="abcdef",
        )
        order.cancel(broker=broker)
        broker.order_cancel.assert_called_once()
        kwargs = dict(order_id="abcdef")
        assert broker.order_cancel.call_args_list[0] == call(**kwargs)


def test_simple_order_do_not_execute_more_than_once():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.return_value = "aaabbb"
        order = Order(
            symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650
        )
        for i in range(10):
            order.execute(broker=broker, exchange="NSE", variety="regular")
        broker.order_place.assert_called_once()


def test_simple_order_do_not_execute_completed_order():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            filled_quantity=10,
        )
        for i in range(10):
            order.execute(broker=broker, exchange="NSE", variety="regular")
        assert broker.order_place.call_count == 0


def test_order_expires():
    known = pendulum.datetime(2021, 1, 1, 12, tz="local")
    with pendulum.test(known):
        order = Order(symbol="aapl", side="buy", quantity=10)
        assert order.expires_in == (60 * 60 * 12) - 1
    order = Order(symbol="aapl", side="buy", quantity=10, expires_in=600)
    assert order.expires_in == 600
    order = Order(symbol="aapl", side="buy", quantity=10, expires_in=-600)
    assert order.expires_in == 600


def test_order_expiry_times():
    known = pendulum.datetime(2021, 1, 1, 9, 30, tz="UTC")
    pendulum.set_test_now(known)
    order = Order(symbol="aapl", side="buy", quantity=10, expires_in=60)
    assert order.expires_in == 60
    assert order.time_to_expiry == 60
    assert order.time_after_expiry == 0
    known = known.add(seconds=40)
    pendulum.set_test_now(known)
    assert order.time_to_expiry == 20
    assert order.time_after_expiry == 0
    known = known.add(seconds=60)
    pendulum.set_test_now(known)
    assert order.time_to_expiry == 0
    assert order.time_after_expiry == 40
    pendulum.set_test_now()


def test_order_has_expired():
    known = pendulum.datetime(2021, 1, 1, 10, tz="UTC")
    pendulum.set_test_now(known)
    order = Order(symbol="aapl", side="buy", quantity=10, expires_in=60)
    assert order.has_expired is False
    known = known.add(seconds=60)
    pendulum.set_test_now(known)
    assert order.has_expired is True
    pendulum.set_test_now()


def test_order_has_parent():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.has_parent is False
    com = CompoundOrder(broker=Broker())
    com.add_order(symbol="aapl", side="buy", quantity=10)
    com.orders[0].has_parent is True


def test_compound_order_check_flags_convert_to_market_after_expiry():
    known = pendulum.datetime(2021, 1, 1, 10)
    pendulum.set_test_now(known)
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        com = CompoundOrder(broker=broker)
        com.add_order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            order_id="abcdef",
            expires_in=30,
            convert_to_market_after_expiry=True,
        )
        com.execute_all()
        com.check_flags()
        known = known.add(seconds=30)
        pendulum.set_test_now(known)
        com.check_flags()
        broker.order_modify.assert_called_once()
    pendulum.set_test_now()


def test_compound_order_check_flags_cancel_after_expiry():
    known = pendulum.datetime(2021, 1, 1, 10)
    pendulum.set_test_now(known)
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        com = CompoundOrder(broker=broker)
        com.add_order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            order_id="abcdef",
            expires_in=30,
        )
        com.execute_all()
        com.check_flags()
        known = known.add(seconds=30)
        pendulum.set_test_now(known)
        com.check_flags()
        broker.order_cancel.assert_called_once()
    pendulum.set_test_now()


def test_compound_order_completed_orders(simple_compound_order):
    order = simple_compound_order
    assert len(order.completed_orders) == 2
    order.orders[-1].status = "COMPLETE"
    order.orders[-1].filled_quantity = 12
    assert len(order.completed_orders) == 3


def test_compound_order_pending_orders(simple_compound_order):
    order = simple_compound_order
    assert len(order.pending_orders) == 1


def test_order_create_db():
    order = Order(symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris")
    con = create_db()
    assert type(con) == Database
    for i in range(10):
        con["orders"].insert({"symbol": "aapl", "quantity": i})
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 10


def test_order_create_db_primary_key_duplicate_error():
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", id="primary_id"
    )
    con = create_db()
    with pytest.raises(sqlite3.IntegrityError):
        for i in range(3):
            con["orders"].insert({"symbol": "aapl", "quantity": i, "id": order.id})


def test_order_save_to_db():
    con = create_db()
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", connection=con
    )
    commit = order.save_to_db()
    assert commit is True
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 1
    for row in con.query("select * from orders"):
        assert row["symbol"] == "aapl"


def test_order_do_not_save_to_db_if_no_connection():
    order = Order(symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris")
    commit = order.save_to_db()
    assert commit is False


def test_order_save_to_db_update():
    con = create_db()
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", connection=con
    )
    order.save_to_db()
    for i in range(1, 8):
        order.filled_quantity = i
        order.save_to_db()
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 1
    for row in con.query("select * from orders"):
        assert row["filled_quantity"] == 7


def test_order_save_to_db_multiple_orders():
    con = create_db()
    order1 = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", connection=con
    )
    order2 = Order(
        symbol="goog",
        side="sell",
        quantity=20,
        timezone="Europe/Paris",
        connection=con,
        tag="short",
    )
    order1.save_to_db()
    order2.save_to_db()
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 2
    for i in range(10):
        order1.save_to_db()
        order2.save_to_db()
    for row in con.query("select * from orders"):
        if row["symbol"] == "aapl":
            assert row["quantity"] == 10
            assert row["tag"] is None
        elif row["symbol"] == "goog":
            assert row["tag"] == "short"


def test_order_save_to_db_update_order():
    con = create_db()
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", connection=con
    )
    for i in range(3):
        order.update({"filled_quantity": 7, "average_price": 780})
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 1
    for row in con.query("select * from orders"):
        assert row["filled_quantity"] == 7
        assert row["average_price"] == 780


def test_order_save_to_db_dont_update_order_no_connection():
    order = Order(symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris")
    for i in range(3):
        order.update({"filled_quantity": 7, "average_price": 780})
    order.save_to_db()


def test_compound_order_save_to_db(simple_compound_order):
    order = simple_compound_order
    con = order.connection
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 3
    for q, row in zip((20, 10, 12), con.query("select * from orders")):
        assert row["quantity"] == q


def test_compound_order_save_to_db_add_order(simple_compound_order):
    order = simple_compound_order
    con = order.connection
    order.add_order(symbol="beta", quantity=17, side="buy")
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 4
    assert result[-1][0] == "beta"


def test_compound_order_update_orders(simple_compound_order):
    order = simple_compound_order
    con = order.connection
    order.add_order(symbol="beta", quantity=17, side="buy", order_id="dddddd")
    order_data = {
        "cccccc": {
            "order_id": "cccccc",
            "filled_quantity": 12,
            "status": "COMPLETE",
            "average_price": 180,
            "exchange_order_id": "some_exchange_id",
        },
        "dddddd": {
            "order_id": "dddddd",
            "exchange_order_id": "some_hex_id",
            "disclosed_quantity": 5,
        },
    }
    updates = order.update_orders(order_data)
    result = con.query("select * from orders")
    for i, row in enumerate(result):
        if i == 2:
            assert row["average_price"] == 180
        elif i == 3:
            assert row["disclosed_quantity"] == 5
            assert row["exchange_order_id"] == "some_hex_id"


def test_compound_order_update_orders_multiple_connections(simple_compound_order):
    order = simple_compound_order
    con = order.connection
    con2 = create_db()
    order.add_order(
        symbol="beta", quantity=17, side="buy", order_id="dddddd", connection=con2
    )
    order_data = {
        "cccccc": {
            "order_id": "cccccc",
            "filled_quantity": 12,
            "status": "COMPLETE",
            "average_price": 180,
            "exchange_order_id": "some_exchange_id",
        },
        "dddddd": {
            "order_id": "dddddd",
            "exchange_order_id": "some_hex_id",
            "disclosed_quantity": 5,
        },
    }
    updates = order.update_orders(order_data)
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 3
    for i, row in enumerate(con.query("select * from orders")):
        if i == 2:
            assert row["average_price"] == 180
    result = con2.execute("select * from orders").fetchall()
    assert len(result) == 1
    for row in con2.query("select * from orders"):

        assert row["exchange_order_id"] == "some_hex_id"
        assert row["disclosed_quantity"] == 5


def test_compound_order_execute_all_default(compound_order):
    order = compound_order
    order.execute_all()
    assert order.broker.order_place.call_count == 3


def test_compound_order_execute_all_order_args(compound_order):
    order = compound_order
    order.execute_all(variety="regular", exchange="NSE")
    call_args = order.broker.order_place.call_args_list
    for arg in call_args:
        assert arg.kwargs.get("variety") == "regular"
        assert arg.kwargs.get("exchange") == "NSE"


def test_compound_order_execute_all_order_args_class(compound_order):
    order = compound_order
    order.order_args = {"variety": "regular", "exchange": "NSE", "product": "MIS"}
    order.execute_all()
    call_args = order.broker.order_place.call_args_list
    for arg in call_args:
        assert arg.kwargs.get("variety") == "regular"
        assert arg.kwargs.get("exchange") == "NSE"


def test_compound_order_execute_all_order_args_override(compound_order):
    order = compound_order
    order.order_args = {"variety": "regular", "exchange": "NSE", "product": "MIS"}
    order.execute_all(product="CNC")
    call_args = order.broker.order_place.call_args_list
    for arg in call_args:
        assert arg.kwargs.get("variety") == "regular"
        assert arg.kwargs.get("exchange") == "NSE"
        assert arg.kwargs.get("product") == "CNC"


def test_compound_order_add_as_order():
    con = create_db()
    com = CompoundOrder(broker=Paper())
    order = Order(symbol="beta", side="sell", quantity=10)
    assert len(com.orders) == 0
    com.add(order)
    assert len(com.orders) == 1
    assert com.id == com.orders[0].parent_id
    assert com.connection == com.orders[0].connection


def test_compound_order_add_as_order_multiple_connections():
    con = create_db()
    con1 = create_db()
    com = CompoundOrder(broker=Paper(), connection=con)
    order1 = Order(symbol="beta", side="sell", quantity=10)
    order2 = Order(symbol="alphabet", side="buy", quantity=10, connection=con1)
    com.add(order1)
    com.add(order2)
    assert len(com.orders) == 2
    assert com.orders[0].connection == com.connection
    assert com.orders[1].connection == con1


def test_compound_order_save():
    con = create_db()
    com = CompoundOrder(broker=Paper(), connection=con)
    order1 = Order(symbol="beta", side="sell", quantity=10)
    order2 = Order(symbol="alphabet", side="buy", quantity=10)
    com.add(order1)
    com.add(order2)
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 2
    order1.quantity = 5
    order2.quantity = 7
    result = list(con.query("select * from orders"))
    # Result not saved to database since we are editing directly
    assert result[0]["quantity"] == 10
    com.save()
    # Result should now change since we have saved it to database
    result = list(con.query("select * from orders"))
    assert result[0]["quantity"] == 5
    assert result[1]["quantity"] == 7


def test_order_max_modifications():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            order_id="abcdef",
        )
        order.price = 630
        order.modify(broker=broker)
        assert order._num_modifications == 1
        for i in range(100):
            order.modify(broker=broker)
        assert order._num_modifications == 10
        assert order.max_modifications == order._num_modifications


def test_order_max_modifications_change_default():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
            order_id="abcdef",
            max_modifications=3,
        )
        order.price = 630
        for i in range(10):
            order.modify(broker=broker)
        assert order._num_modifications == 3
        order.max_modifications = 5
        for i in range(10):
            order.modify(broker=broker)
        assert order._num_modifications == 5


def test_order_clone():
    order = Order(
        symbol="aapl",
        side="buy",
        quantity=10,
        order_type="LIMIT",
        price=650,
        exchange="nasdaq",
        timezone="America/New_York",
        parent_id="some_random_hex",
    )
    clone = order.clone()
    assert order.id != clone.id
    assert order.parent_id != clone.parent_id
    exclude_keys = ["id", "parent_id", "timestamp"]
    for k, v in order.dict().items():
        if k not in exclude_keys:
            assert getattr(clone, k) == v


def test_order_clone_new_timestamp():
    order = Order(symbol="aapl", side="buy", quantity=10, order_type="LIMIT", price=650)
    clone = order.clone()
    assert clone.timestamp != order.timestamp
    assert clone.timestamp > order.timestamp


def test_new_db():
    """
    Testing new db with its columns
    """
    con = create_db()
    order = Order(symbol="amzn", side="sell", quantity=10, connection=con)
    order.save_to_db()

    # Check newly added columns are available in the database
    keys = ["can_peg", "strategy_id", "portfolio_id", "pseudo_id", "JSON", "error"]
    for row in con.query("select * from orders"):
        for key in keys:
            assert key in row


def test_new_db_with_values():
    con = create_db()
    order = Order(
        symbol="amzn",
        side="sell",
        quantity=10,
        connection=con,
        JSON=json.dumps({"a": 10, "b": [4, 5, 6]}),
        pseudo_id="hex_pseudo_id",
        error="some_error_message",
        tag="this is a tag",
    )
    order.save_to_db()

    # Check newly added columns are available in the database
    for row in con.query("select * from orders"):
        assert row["can_peg"] == 1
        assert row["JSON"] == json.dumps({"a": 10, "b": [4, 5, 6]})
        assert row["tag"] == "this is a tag"
        assert row["is_multi"] == 0
        assert row["last_updated_at"] is None
        retrieved_order = Order(**row)
        assert retrieved_order.can_peg is True
        assert retrieved_order.JSON == {"a": 10, "b": [4, 5, 6]}
        assert retrieved_order.pseudo_id == "hex_pseudo_id"


def test_new_db_all_values():
    con = create_db()
    order = Order(
        symbol="amzn",
        side="sell",
        quantity=10,
        connection=con,
        JSON=json.dumps({"a": 10, "b": [4, 5, 6]}),
        pseudo_id="hex_pseudo_id",
        error="some_error_message",
        timezone="Asia/Kolkata",
    )
    order.save_to_db()

    # Check newly added columns are available in the database
    for row in con.query("select * from orders"):
        retrieved_order = Order(**row)

    expected = retrieved_order.dict()
    exclude_keys = ["connection"]
    for k, v in order.dict().items():
        if k not in exclude_keys:
            assert expected[k] == v


def test_order_modify_quantity(simple_order):
    order = simple_order
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.exchange = "NSE"
        order.modify(broker=broker, price=630, quantity=20, exchange="NFO")
        broker.order_modify.assert_called_once()
        assert order.quantity == 20
        assert order.price == 630


def test_order_modify_by_attribute(simple_order):
    order = simple_order
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.quantity = 100
        order.price = 600
        order.modify(broker=broker, exchange="NSE")
        broker.order_modify.assert_called_once()
        kwargs = broker.order_modify.call_args_list[0].kwargs
        assert kwargs["quantity"] == 100
        assert kwargs["price"] == 600
        assert kwargs["exchange"] == "NSE"


def test_order_modify_extra_attributes(simple_order):
    order = simple_order
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.modify(
            broker=broker, price=630, quantity=20, exchange="NFO", validity="GFD"
        )
        broker.order_modify.assert_called_once()
        kwargs = broker.order_modify.call_args_list[0].kwargs
        assert kwargs["quantity"] == 20
        assert kwargs["price"] == 630
        assert kwargs["validity"] == "GFD"


def test_order_modify_frozen(simple_order):
    order = simple_order
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.modify(
            broker=broker,
            price=630,
            quantity=20,
            exchange="NFO",
            validity="GFD",
            symbol="meta",
            tsym="meta",
        )
        kwargs = broker.order_modify.call_args_list[0].kwargs
        assert "symbol" not in kwargs
        assert kwargs["tsym"] == "meta"


def test_order_is_pending_canceled():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.is_pending is True
    order.filled_quantity, order.cancelled_quantity = 5, 0
    assert order.is_pending is True
    order.status = "CANCELED"
    assert order.is_pending is False


def test_order_is_pending_rejected():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.is_pending is True
    order.status = "REJECTED"
    assert order.filled_quantity == order.cancelled_quantity == 0
    assert order.is_pending is False


def test_order_is_done():
    order = Order(symbol="aapl", side="buy", quantity=10, filled_quantity=10)
    assert order.is_complete is True
    assert order.is_done is True
    order = Order(
        symbol="aapl", side="buy", quantity=10, filled_quantity=5, cancelled_quantity=5
    )
    assert order.is_done is True


def test_order_is_done_not_complete():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.is_done is False
    order.status = "CANCELED"
    assert order.is_complete is False
    assert order.is_pending is False
    assert order.is_done is True

    order = Order(symbol="aapl", side="buy", quantity=10)
    order.status = "REJECTED"
    assert order.is_complete is False
    assert order.is_pending is False
    assert order.is_done is True


def test_simple_order_cancel_none():
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order = Order(
            symbol="aapl",
            side="buy",
            quantity=10,
            order_type="LIMIT",
            price=650,
        )
        order.cancel(broker=broker)
        broker.order_cancel.assert_not_called()


def test_order_timezone():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.timezone == "local"
    assert order.timestamp.timezone.name == pendulum.now(tz="local").timezone_name


def test_order_update_pending_quantity():
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.pending_quantity == order.quantity == 10
    assert order.filled_quantity == 0
    order.update({"filled_quantity": 5})
    assert order.pending_quantity == order.filled_quantity == 5


def test_order_update_pending_quantity_in_data():
    """
    Data is inconsistent with the order but we
    take the broker data as the true version
    """
    order = Order(symbol="aapl", side="buy", quantity=10)
    assert order.pending_quantity == order.quantity == 10
    assert order.filled_quantity == 0
    order.update({"filled_quantity": 5, "pending_quantity": 2})
    assert order.pending_quantity == 2
    assert order.filled_quantity == 5


def test_order_lock_no_lock():
    known = pendulum.datetime(2022, 1, 1, 10, 10)
    with patch("omspy.brokers.paper.Paper") as broker:
        with pendulum.test(known):
            order = Order(symbol="aapl", side="buy", quantity=10)
            order.execute(broker=broker)
        for i in range(10):
            with pendulum.test(known.add(seconds=i + 1)):
                order.modify(broker=broker)
        broker.order_place.assert_called_once()
        assert broker.order_modify.call_count == 10
        for i in range(6):
            with pendulum.test(known.add(seconds=i + 1)):
                order.cancel(broker=broker)
        assert broker.order_cancel.call_count == 6


def test_order_lock_modify_and_cancel():
    known = pendulum.datetime(2022, 1, 1, 10, 10)
    with patch("omspy.brokers.paper.Paper") as broker:
        with pendulum.test(known):
            order = Order(symbol="aapl", side="buy", quantity=10)
            order.execute(broker=broker)
        for i in range(10):
            with pendulum.test(known.add(seconds=i + 1)):
                if i == 5:
                    order.add_lock(1, 3)
                order.modify(broker=broker)
        assert broker.order_modify.call_count == 6
        for i in range(6):
            with pendulum.test(known):
                order.add_lock(2, 10)
            with pendulum.test(known.add(seconds=i + 1)):
                order.cancel(broker=broker)
        broker.order_cancel.assert_not_called()


def test_order_lock_cancel():
    known = pendulum.datetime(2022, 1, 1, 10, 10)
    with patch("omspy.brokers.paper.Paper") as broker:
        with pendulum.test(known):
            order = Order(symbol="aapl", side="buy", quantity=10)
            order.execute(broker=broker)
        for i in range(10):
            with pendulum.test(known.add(seconds=i + 1)):
                if i % 2 == 0:
                    order.cancel(broker=broker)
                if i % 6 == 0:
                    order.add_lock(2, 4)

        assert broker.order_cancel.call_count == 2


def test_compound_order_add_id_if_not_exist(compound_order):
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.id = None
    assert order.id is None
    compound_order.add(order)
    assert compound_order.orders[-1].id is not None


def test_order_modify_args_to_add(simple_order):
    ## Add some properties
    order = simple_order
    order.client_id = "abcd1234"
    order.exchange = "nyse"
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.modify(broker=broker, attribs_to_copy=("client_id",), price=600)
        broker.order_modify.assert_called_once()
        assert order.price == 600
        kwargs = broker.order_modify.call_args_list[0].kwargs
        expected = dict(
            order_id="abcdef",
            quantity=10,
            price=600,
            trigger_price=0,
            order_type="LIMIT",
            disclosed_quantity=0,
            client_id="abcd1234",
        )
        assert kwargs == expected


def test_order_modify_args_to_add_no_args(simple_order):
    ## Add some properties
    order = simple_order
    order.client_id = "abcd1234"
    order.exchange = "nyse"
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.modify(broker=broker, attribs_to_copy=("transform", "segment"), price=600)
        broker.order_modify.assert_called_once()
        assert order.price == 600
        kwargs = broker.order_modify.call_args_list[0].kwargs
        expected = dict(
            order_id="abcdef",
            quantity=10,
            price=600,
            trigger_price=0,
            order_type="LIMIT",
            disclosed_quantity=0,
        )
        assert kwargs == expected


def test_order_modify_args_to_add_override(simple_order):
    ## Add some properties
    order = simple_order
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.modify(
            broker=broker, attribs_to_copy=("exchange",), price=600, exchange="nasdaq"
        )
        broker.order_modify.assert_called_once()
        assert order.price == 600
        kwargs = broker.order_modify.call_args_list[0].kwargs
        expected = dict(
            order_id="abcdef",
            quantity=10,
            price=600,
            trigger_price=0,
            order_type="LIMIT",
            disclosed_quantity=0,
            exchange="nasdaq",
        )
        assert kwargs == expected


def test_order_modify_args_dont_modify_frozen(simple_order):
    ## Add some properties
    order = simple_order
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        order.modify(broker=broker, attribs_to_copy=("symbol", "side"), price=600)
        broker.order_modify.assert_called_once()
        assert order.price == 600
        kwargs = broker.order_modify.call_args_list[0].kwargs
        expected = dict(
            order_id="abcdef",
            quantity=10,
            price=600,
            trigger_price=0,
            order_type="LIMIT",
            disclosed_quantity=0,
            symbol="aapl",
            side="buy",
        )
        assert kwargs == expected
        order.modify(
            broker=broker,
            attribs_to_copy=("symbol", "side"),
            price=600,
            symbol="goog",
            side="sell",
        )
        kwargs = broker.order_modify.call_args_list[1].kwargs
        assert kwargs == expected


def test_order_execute_attribs_to_copy(simple_order, order_kwargs):
    order = simple_order
    order.order_id = None
    order = Order(
        symbol="aapl",
        side="buy",
        quantity=10,
        order_type="LIMIT",
        price=650,
        exchange="nyse",
    )

    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(100000, 100010)
        order_kwargs["exchange"] = "nyse"
        order.execute(broker=broker, attribs_to_copy={"exchange"})
        broker.order_place.assert_called_once()
        kwargs = broker.order_place.call_args_list[0].kwargs
        assert kwargs == order_kwargs


def test_order_execute_attribs_to_copy_broker(simple_order, order_kwargs):
    order = simple_order
    order.order_id = None
    order.exchange = "nyse"
    broker = Paper()
    broker.attribs_to_copy_execute = ("exchange", "client_id")
    order_kwargs["exchange"] = "nyse"
    kwargs = order.execute(broker=broker)
    assert kwargs == order_kwargs


def test_order_execute_attribs_to_copy_broker2(simple_order, order_kwargs):
    order = simple_order
    order.order_id = None
    order.exchange = "nyse"
    order.client_id = "abcd1234"
    broker = Paper()
    broker.attribs_to_copy_execute = ("exchange", "client_id")
    order_kwargs["exchange"] = "nyse"
    order_kwargs["client_id"] = "abcd1234"
    kwargs = order.execute(broker=broker)
    assert kwargs == order_kwargs


def test_order_execute_attribs_to_copy_override(simple_order, order_kwargs):
    order = simple_order
    order.order_id = None
    order.exchange = "nyse"
    order.client_id = "abcd1234"
    broker = Paper()
    order_kwargs["exchange"] = "nasdaq"
    order_kwargs["client_id"] = "xyz12345"
    order_args = order.execute(broker=broker, exchange="nasdaq", client_id="xyz12345")
    assert order_args == order_kwargs


def test_get_other_args_from_attribs(simple_order):
    order = simple_order
    order.exchange = "nyse"
    order.client_id = "abcd1234"
    broker = Paper()
    broker.attribs_to_copy_execute = ("exchange", "client_id")
    assert order._get_other_args_from_attribs(
        broker, "attribs_to_copy_execute"
    ) == dict(exchange="nyse", client_id="abcd1234")


def test_order_modify_attribs_to_copy_broker(simple_order, order_kwargs):
    order = simple_order
    order.exchange = "nyse"
    order.client_id = "abcd1234"
    broker = Paper()
    broker.attribs_to_copy_modify = ("exchange", "client_id")
    order_kwargs["exchange"] = "nyse"
    order_kwargs["client_id"] = "abcd1234"
    order_kwargs["price"] = 700
    order_kwargs["order_id"] = "abcdef"
    del order_kwargs["symbol"]
    del order_kwargs["side"]
    with patch("omspy.brokers.paper.Paper.order_modify") as modify:
        order.modify(broker=broker, price=700)
        modify.assert_called_once()
        kwargs = modify.call_args_list[0].kwargs
        assert kwargs == order_kwargs


def test_order_cancel_attribs_to_copy_broker(simple_order):
    order = simple_order
    order.client_id = "abcd1234"
    broker = Paper()
    broker.attribs_to_copy_cancel = ("client_id",)
    with patch("omspy.brokers.paper.Paper.order_cancel") as cancel:
        order.cancel(broker=broker)
        cancel.assert_called_once()
        kwargs = cancel.call_args_list[0].kwargs
        assert kwargs == dict(order_id="abcdef", client_id="abcd1234")
