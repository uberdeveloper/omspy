import pytest
from unittest.mock import patch, call
from omspy.order import *
from omspy.brokers.paper import Paper
from collections import Counter
import pendulum
from copy import deepcopy
import sqlite3


@pytest.fixture
def simple_compound_order():
    com = CompoundOrder(broker=Paper())
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
    print(test_input)
    assert get_option(*test_input) == expected


def test_order_update_simple():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.update(
        {"filled_quantity": 7, "average_price": 912, "exchange_order_id": "abcd"}
    )
    assert order.filled_quantity == 7
    assert order.average_price == 912
    assert order.exchange_order_id == "abcd"


def test_order_update_non_attribute():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.update(
        {"filled_quantity": 7, "average_price": 912, "message": "not in attributes"}
    )
    assert order.filled_quantity == 7
    assert hasattr(order, "message") is False


def test_order_update_do_not_update_when_complete():
    order = Order(symbol="aapl", side="buy", quantity=10)
    order.filled_quantity = 10
    order.update({"average_price": 912})
    assert order.average_price == 0
    order.filled_quantity = 7
    order.update({"average_price": 912})
    assert order.average_price == 912
    order.average_price = 0
    # This is wrong; this should never be updated directly
    order.status = "COMPLETE"
    assert order.average_price == 0
    assert order.filled_quantity == 7


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
    assert updates == {"aaaaaa": False, "bbbbbb": False, "cccccc": True}
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


def test_simple_order_modify():
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
        print(call(**kwargs))
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
        broker.order_place.call_count == 0


def test_order_expires():
    known = pendulum.datetime(2021, 1, 1, 12, tz="UTC")
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
    assert type(con) == sqlite3.Connection
    with con:
        for i in range(10):
            con.execute(
                "insert into orders (symbol,quantity) values (?,?)", ("aapl", i)
            )

    result = con.execute("select * from orders").fetchall()
    assert len(result) == 10


def test_order_create_db_primary_key_duplicate_error():
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", id="primary_id"
    )
    con = create_db()
    with pytest.raises(sqlite3.IntegrityError):
        with con:
            for i in range(3):
                con.execute(
                    "insert into orders (symbol,quantity,id) values (?,?,?)",
                    ("aapl", i, order.id),
                )


def test_order_save_to_db():
    con = create_db()
    con.row_factory = sqlite3.Row
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", connection=con
    )
    order.save_to_db()
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 1
    for row in result:
        assert row["symbol"] == "aapl"


def test_order_save_to_db():
    con = create_db()
    con.row_factory = sqlite3.Row
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", connection=con
    )
    commit = order.save_to_db()
    assert commit is True
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 1
    for row in result:
        assert row["symbol"] == "aapl"


def test_order_do_not_save_to_db_if_no_connection():
    order = Order(symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris")
    commit = order.save_to_db()
    assert commit is False


def test_order_save_to_db_update():
    con = create_db()
    con.row_factory = sqlite3.Row
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", connection=con
    )
    order.save_to_db()
    for i in range(1, 8):
        order.filled_quantity = i
        order.save_to_db()
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 1
    for row in result:
        assert row["filled_quantity"] == 7


def test_order_save_to_db_multiple_orders():
    con = create_db()
    con.row_factory = sqlite3.Row
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
    for row in result:
        if row["symbol"] == "aapl":
            assert row["quantity"] == 10
            assert row["tag"] is None
        elif row["symbol"] == "goog":
            assert row["tag"] == "short"


def test_order_save_to_db_update_order():
    con = create_db()
    con.row_factory = sqlite3.Row
    order = Order(
        symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris", connection=con
    )
    for i in range(3):
        order.update({"filled_quantity": 7, "average_price": 780})
    result = con.execute("select * from orders").fetchall()
    assert len(result) == 1
    for row in result:
        assert row["filled_quantity"] == 7
        assert row["average_price"] == 780


def test_order_save_to_db_dont_update_order_no_connection():
    order = Order(symbol="aapl", side="buy", quantity=10, timezone="Europe/Paris")
    for i in range(3):
        order.update({"filled_quantity": 7, "average_price": 780})
    order.save_to_db()
