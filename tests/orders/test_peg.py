from omspy.orders.peg import *
import pytest
from omspy.brokers.paper import Paper
from omspy.order import create_db, Order
import pendulum
from unittest.mock import patch, call
from omspy.brokers.zerodha import Zerodha
from pydantic import ValidationError


@pytest.fixture
def existing_peg():
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10009)
        broker.order_modify.side_effect = range(10000, 10009)
        with pendulum.test(known):
            order = Order(
                symbol="goog",
                quantity=200,
                side="buy",
                price=250,
                timezone="local",
                convert_to_market_after_expiry=True,
            )
            peg = PegExisting(order=order, broker=broker, peg_every=3, duration=10)
            return peg


@pytest.fixture
def order_list():
    # Since order locks are acquired based on current time
    # we are using time based analysis
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    with pendulum.test(known):
        orders = [
            Order(symbol="aapl", side="buy", quantity=10),
            Order(symbol="goog", side="buy", quantity=10),
            Order(symbol="amzn", side="buy", quantity=10),
        ]
        return orders


@pytest.fixture
def sequential_peg(order_list):
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10099)
        broker.order_modify.side_effect = range(10000, 10099)
        with pendulum.test(known):
            order_list.append(Order(symbol="dow", side="buy", quantity=10))
            peg = PegSequential(orders=order_list, broker=broker)
            return peg


def test_basic_peg():
    peg = BasicPeg(symbol="aapl", side="buy", quantity=100, broker=Paper())
    assert peg.count == 1
    assert peg.orders[0].order_type == "LIMIT"
    assert peg.ltp["aapl"] == 0.0
    assert peg.timezone == "local"


def test_peg_market_defaults():
    known = pendulum.datetime(2022, 1, 1, 10)
    with pendulum.test(known):
        peg = PegMarket(symbol="aapl", side="buy", quantity=100, broker=Paper())
        assert peg.num_pegs == 0
        assert peg._max_pegs == 6
        assert peg._expire_at == pendulum.datetime(2022, 1, 1, 10, minute=1)
        assert peg.next_peg == pendulum.datetime(2022, 1, 1, 10, second=10)


def test_peg_market_connection():
    connection = create_db()
    known = pendulum.datetime(2022, 1, 1, 10)
    with pendulum.test(known):
        peg = PegMarket(
            symbol="aapl",
            side="buy",
            quantity=100,
            broker=Paper(),
            connection=connection,
        )
        assert peg.num_pegs == 0
        assert peg._max_pegs == 6
        assert peg._expire_at == pendulum.datetime(2022, 1, 1, 10, minute=1)
        assert peg.next_peg == pendulum.datetime(2022, 1, 1, 10, second=10)
        assert peg.connection == connection
        assert peg.orders[0].connection == connection


def test_peg_market_change_defaults():
    known = pendulum.datetime(2022, 1, 1, 10, 5, 45, tz="Asia/Kolkata")
    with pendulum.test(known):
        peg = PegMarket(
            symbol="aapl",
            side="buy",
            quantity=100,
            broker=Paper(),
            duration=150,
            peg_every=20,
            timezone="Asia/Kolkata",
            exchange="nse",
            client_id="ab1111",
            order_type="MARKET",
        )
        assert peg.num_pegs == 0
        assert peg._max_pegs == 7
        assert peg._expire_at == pendulum.datetime(
            2022, 1, 1, 10, minute=8, second=15, tz="Asia/Kolkata"
        )
        assert peg.next_peg == pendulum.datetime(
            2022, 1, 1, 10, minute=6, second=5, tz="Asia/Kolkata"
        )
        assert peg.orders[0].exchange == "nse"
        assert peg.orders[0].client_id == "ab1111"
        assert peg.orders[0].order_type == "LIMIT"


def test_peg_market_update_ltp():
    peg = PegMarket(symbol="aapl", side="buy", quantity=100, broker=Paper())
    assert peg.ref_price == 0
    peg.update_ltp({"aapl": 158})
    assert peg.ref_price == 158
    peg.update_ltp({"aap": 168})
    assert peg.ref_price == 158
    peg.update_ltp({"aapl": 161})
    assert peg.ref_price == 161


@patch("omspy.brokers.paper.Paper")
def test_peg_market_next_peg(broker):
    known = pendulum.datetime(2022, 1, 1, 10)
    pendulum.set_test_now(known)
    peg = PegMarket(
        symbol="aapl",
        side="buy",
        quantity=100,
        broker=broker,
        order_args={"product": "mis", "validity": "day"},
    )
    assert peg.next_peg == pendulum.now().add(seconds=10)
    pendulum.set_test_now(known.add(seconds=13))
    peg.run()
    assert peg.next_peg == pendulum.datetime(2022, 1, 1, 10, second=23)
    broker.order_modify.assert_called_once()
    pendulum.set_test_now(known.add(seconds=24))
    peg.run()
    assert peg.next_peg == pendulum.datetime(2022, 1, 1, 10, second=34)
    assert broker.order_modify.call_count == 2


@patch("omspy.brokers.paper.Paper")
def test_peg_market_cancel_on_expiry(broker):
    known = pendulum.datetime(2022, 1, 1, 10)
    pendulum.set_test_now(known)
    peg = PegMarket(
        symbol="aapl",
        side="buy",
        quantity=100,
        broker=broker,
        order_args={"product": "mis", "validity": "day"},
    )
    peg.convert_to_market_after_expiry = False
    peg.orders[0].order_id = "abcdef"
    pendulum.set_test_now(known.add(seconds=61))
    peg.run()
    broker.order_cancel.assert_called_once()


@patch("omspy.brokers.paper.Paper")
def test_peg_market_execute_price(broker):
    known = pendulum.datetime(2022, 1, 1, 10)
    pendulum.set_test_now(known)
    peg = PegMarket(symbol="aapl", side="buy", quantity=100, broker=broker)
    assert peg.orders[0].price is None
    peg.update_ltp({"aapl": 107})
    peg.execute()
    assert peg.orders[0].price == 107


@patch("omspy.brokers.paper.Paper")
def test_peg_market_run_is_pending(broker):
    known = pendulum.datetime(2022, 1, 1, 10)
    pendulum.set_test_now(known)
    peg = PegMarket(symbol="aapl", side="buy", quantity=100, broker=broker)
    peg.update_ltp({"aapl": 107})
    peg.execute()
    peg.orders[0].filled_quantity = 100
    peg.orders[0].average_price = 106.75
    pendulum.set_test_now(known.add(seconds=11))
    peg.run()
    pendulum.set_test_now(known.add(seconds=22))
    peg.run()
    pendulum.set_test_now(known.add(seconds=33))
    peg.run()
    broker.order_place.assert_called_once()
    broker.order_modify.assert_not_called()


def test_existing_peg_defaults():
    order = Order(symbol="amzn", quantity=20, side="buy")
    assert order.order_type == "MARKET"
    broker = Zerodha(*list("abcdef"))
    peg = PegExisting(order=order, broker=broker)
    assert peg.order.order_type == "LIMIT"
    known = pendulum.datetime(2022, 1, 1, 9, 15, 30)
    with pendulum.test(known):
        peg = PegExisting(order=order, broker=broker, duration=10, peg_every=3)
        assert peg.num_pegs == 0
        assert peg._max_pegs == 3


def test_existing_peg_order_place(existing_peg):
    peg = existing_peg
    peg.execute()
    peg.broker.order_place.assert_called_once()
    call_args = peg.broker.order_place.call_args_list
    assert call_args[0].kwargs == dict(
        symbol="GOOG",
        quantity=200,
        side="BUY",
        price=250,
        order_type="LIMIT",
        disclosed_quantity=0,
        trigger_price=0,
    )


def test_existing_peg_order_place_order_args(existing_peg):
    peg = existing_peg
    peg.order_args = {"product": "MIS", "exchange": "NFO"}
    peg.execute()
    peg.broker.order_place.assert_called_once()
    call_args = peg.broker.order_place.call_args_list
    assert call_args[0].kwargs == dict(
        symbol="GOOG",
        quantity=200,
        side="BUY",
        price=250,
        order_type="LIMIT",
        disclosed_quantity=0,
        trigger_price=0,
        exchange="NFO",
        product="MIS",
    )


def test_existing_peg_order_modify_args(existing_peg):
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    peg = existing_peg
    peg.order_args = {"product": "MIS", "exchange": "NFO"}
    peg.modify_args = {"tag": "modified"}
    peg.execute()
    peg.broker.order_place.assert_called_once()
    with pendulum.test(known.add(seconds=10)):
        peg.run(ltp=120)
        peg.broker.order_modify.assert_called_once()
    call_args = peg.broker.order_modify.call_args_list
    assert call_args[0].kwargs == dict(
        order_id=10000,
        quantity=200,
        price=120,
        trigger_price=0.0,
        disclosed_quantity=0.0,
        tag="modified",
        order_type="LIMIT",
    )


@patch("omspy.brokers.zerodha.Zerodha")
def test_existing_peg_run(broker):
    known = pendulum.datetime(2022, 4, 1, 10, 0)
    with pendulum.test(known):
        order = Order(symbol="amzn", quantity=20, side="buy")
        peg = PegExisting(order=order, broker=broker)
        peg.execute()
        broker.order_place.assert_called_once()
        peg.run(ltp=228)
        assert order.price is None
    known = known.add(seconds=11)
    with pendulum.test(known):
        peg.run(ltp=228)
        assert order.price == 228
        broker.order_modify.assert_called_once()


def test_existing_peg_validation_pending():
    known = pendulum.datetime(2022, 4, 1, 10, 0)
    order = Order(symbol="amzn", quantity=20, side="buy", status="COMPLETE")
    with pytest.raises(ValidationError):
        with pendulum.test(known):
            peg = PegExisting(order=order)
    order.status = None
    order.filled_quantity = 20
    with pytest.raises(ValidationError):
        with pendulum.test(known):
            peg = PegExisting(order=order)


def test_existing_peg_full_run(existing_peg):
    peg = existing_peg
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    order, broker = peg.order, peg.broker
    assert order.order_type == "LIMIT"
    with pendulum.test(known):
        peg.execute()
        broker.order_place.assert_called_once()
        for price in (271, 264, 268):
            peg.run(ltp=price)
            broker.order_modify.assert_not_called()
    known = known.add(seconds=4)
    with pendulum.test(known):
        order.filled_quantity = 122
        peg.run(ltp=252)
        assert order.price == 252
        broker.order_modify.assert_called_once()
    known = known.add(seconds=3)
    with pendulum.test(known):
        order.filled_quantity = 122
        peg.run(ltp=252)
        assert order.price == 252
        broker.order_modify.assert_called_once()
    known = known.add(seconds=4)
    with pendulum.test(known):
        peg.run(ltp=250.9)
        assert broker.order_modify.call_count == 2
        call_args = broker.order_modify.call_args_list
        expected_kwargs = dict(
            order_id=10000,
            quantity=200,
            price=252,
            trigger_price=0,
            order_type="MARKET",
            disclosed_quantity=0,
        )
        assert call_args[-1].kwargs == expected_kwargs
    peg.order.filled_quantity = 200
    peg.run(ltp=234)
    assert peg.done is True


def test_existing_peg_full_run_cancel(existing_peg):
    peg = existing_peg
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    order, broker = peg.order, peg.broker
    order.convert_to_market_after_expiry = False
    with pendulum.test(known):
        peg.execute()
        broker.order_place.assert_called_once()
    known = known.add(seconds=4)
    with pendulum.test(known):
        peg.run(ltp=252)
        assert order.price == 252
        broker.order_modify.assert_called_once()
    known = known.add(seconds=10)
    with pendulum.test(known):
        peg.run(ltp=250.9)
        broker.order_cancel.assert_called_once()
        broker.order_place.assert_called_once()
        broker.order_modify.assert_called_once()
        broker.order_cancel.assert_called_once()
    peg.order.status = "CANCELED"
    peg.run(ltp=234)
    assert peg.done is True


def test_existing_peg_run_complete(existing_peg):
    # Do not call modify if all quantity is filled or order is complete
    peg = existing_peg
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    order, broker = peg.order, peg.broker
    order.convert_to_market_after_expiry = False
    with pendulum.test(known):
        peg.execute()
        broker.order_place.assert_called_once()
    known = known.add(seconds=4)
    with pendulum.test(known):
        order.filled_quantity = 200
        peg.run(ltp=252)
        broker.order_modify.assert_not_called()
        assert peg.done is True


def test_existing_peg_run_order_lock(existing_peg):
    peg = existing_peg
    peg.peg_every = 2
    peg.lock_duration = 4
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    order, broker = peg.order, peg.broker
    with pendulum.test(known):
        peg.execute()
        broker.order_place.assert_called_once()
    known = known.add(seconds=4)
    with pendulum.test(known):
        peg.run(ltp=252)
        broker.order_modify.assert_called_once()
    known = known.add(seconds=5)
    with pendulum.test(known):
        peg.run(ltp=252)
        assert broker.order_modify.call_count == 2
    known = known.add(seconds=5)
    with pendulum.test(known):
        peg.run(ltp=252)
        assert broker.order_modify.call_count == 3


def test_peg_sequential_defaults(order_list):
    orders = order_list
    known = pendulum.datetime(2022, 1, 1, 9, 10)
    with pendulum.test(known):
        peg = PegSequential(orders=orders)
        assert len(peg.orders) == 3
        assert peg.timezone is None
        assert peg.duration == 12
        assert peg.peg_every == 4
        assert peg.done is False
        assert peg._start_time == known


def test_peg_sequential_valid_orders():
    orders = [
        Order(symbol="aapl", side="buy", quantity=10),
        Order(symbol="goog", side="buy", quantity=10),
        Order(symbol="amzn", side="buy", quantity=10, filled_quantity=10),
    ]
    with pytest.raises(ValidationError):
        peg = PegSequential(orders=orders)


def test_peg_sequential_completed_orders(order_list):
    orders = order_list
    peg = PegSequential(orders=orders)
    assert peg.completed == []
    orders[-1].filled_quantity = 10
    assert peg.completed == orders[-1:]


def test_peg_sequential_pending_orders(order_list):
    orders = order_list
    peg = PegSequential(orders=orders)
    assert peg.pending == orders
    for order in orders:
        order.status = "COMPLETE"
    assert peg.pending == []


def test_peg_sequential_pending_orders(order_list):
    orders = order_list
    peg = PegSequential(orders=orders)
    assert peg.all_complete is False
    orders[-1].filled_quantity = 10
    assert peg.all_complete is False
    for order in orders:
        order.status = "COMPLETE"
    assert peg.all_complete is True


def test_peg_sequential_get_current_order(order_list):
    orders = order_list
    peg = PegSequential(orders=orders, peg_every=3)
    peg_args = dict(duration=12, peg_every=3, lock_duration=2)
    peg_order = PegExisting(order=orders[0], **peg_args)
    assert peg.get_current_order() == peg_order
    assert peg.order is None
    orders[0].filled_quantity = 10
    peg_order = PegExisting(order=orders[1], **peg_args)
    assert peg.get_current_order() == peg_order
    orders[1].filled_quantity = 5
    assert peg.get_current_order() == peg_order
    orders[1].cancelled_quantity = 5
    assert peg.get_current_order() != peg_order
    assert peg.get_current_order() == PegExisting(order=orders[-1], **peg_args)
    orders[2].status = "COMPLETE"
    assert peg.get_current_order() is None


def test_peg_sequential_set_current_order(order_list):
    orders = order_list
    peg = PegSequential(orders=orders, peg_every=3)
    peg_args = dict(duration=12, peg_every=3, lock_duration=2)
    peg_order = PegExisting(order=orders[0], **peg_args)
    assert peg.order is None
    peg.set_current_order()
    assert peg.order == peg_order
    orders[0].filled_quantity = 10
    peg_order = PegExisting(order=orders[1], **peg_args)
    peg.set_current_order()
    assert peg.order == peg_order
    orders[1].filled_quantity = 5
    orders[1].cancelled_quantity = 5
    orders[2].status = "COMPLETE"
    peg.set_current_order()
    assert peg.order is None


def test_peg_sequential_set_current_order_existing(order_list):
    # Set current order only when there is no existing order
    # and check the timestamp is the same for the same order
    orders = order_list
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    with pendulum.test(known):
        peg = PegSequential(orders=orders, peg_every=3)
        peg_args = dict(duration=12, peg_every=3, lock_duration=2)
        peg_order = PegExisting(order=orders[0], **peg_args)
        assert peg.order is None
        peg.set_current_order()
        assert peg.order._expire_at == known.add(seconds=12)
    for i in range(10):
        k = known.add(seconds=i)
        with pendulum.test(k):
            peg.set_current_order()
            assert peg.order._expire_at == known.add(seconds=12)


def test_peg_sequential_has_expired(order_list):
    orders = order_list
    known = pendulum.datetime(2022, 1, 1, 10, 10)
    with pendulum.test(known):
        peg = PegSequential(orders=order_list, duration=10)
        assert peg.has_expired is False
    with pendulum.test(known.add(seconds=25)):
        assert peg.has_expired is False
    with pendulum.test(known.add(seconds=31)):
        assert peg.has_expired is True

    with pendulum.test(known):
        peg = PegSequential(orders=order_list + order_list, duration=30)
    with pendulum.test(known.add(seconds=180)):
        assert peg.has_expired is False
    with pendulum.test(known.add(seconds=181)):
        assert peg.has_expired is True


def test_peg_sequential_run(sequential_peg):
    peg = sequential_peg
    assert len(peg.orders) == 4
    assert len(peg.pending) == 4
    assert len(peg.completed) == 0
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    peg.run(ltp=ltp1)

    assert peg.order.order.symbol == "aapl"
    with pendulum.test(known.add(seconds=15)):
        assert peg.order.order.symbol == "aapl"
        peg.broker.order_place.assert_called_once()
        for i in range(4):
            peg.orders[i].filled_quantity = 10
            assert len(peg.pending) == 4 - (i + 1)
            assert len(peg.completed) == i + 1
            peg.run(ltp=ltp1)
    assert peg.broker.order_place.call_count == 4
    assert peg.all_complete is True


def test_peg_sequential_run_modify(sequential_peg):
    peg = sequential_peg
    assert len(peg.completed) == 0
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    peg.run(ltp=ltp1)
    for i in range(30):
        k = known.add(seconds=10 + i)
        with pendulum.test(k):
            if i % 7 == 0:
                if peg.order:
                    peg.order.order.filled_quantity = 10
            peg.run(ltp=ltp1)
    assert peg.broker.order_place.call_count == 4
    assert peg.broker.order_modify.call_count == 3
    assert peg.all_complete is True


def test_peg_sequential_execute_all(sequential_peg):
    peg = sequential_peg
    peg.execute_all()
    assert peg.broker.order_place.call_count == 4


def test_peg_sequential_cancel_all(sequential_peg):
    peg = sequential_peg
    peg.cancel_all()
    peg.broker.order_cancel.assert_not_called()
    for (order, num) in zip(peg.orders, range(10000, 10009)):
        order.order_id = num
    peg.cancel_all()
    assert peg.broker.order_cancel.call_count == 4


def test_peg_sequential_dont_execute_after_time(sequential_peg):
    peg = sequential_peg
    print(peg.duration, peg.peg_every)
    print([o.symbol for o in peg.orders])
    print([o.convert_to_market_after_expiry for o in peg.orders])
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    for i in (5, 10, 30, 50, 60):
        k = known.add(seconds=i)
        if i == 10:
            peg.orders[0].filled_quantity = 10
        if i > 40:
            for order in peg.orders[1:]:
                if order.status is None:
                    order.status = "CANCELED"
        with pendulum.test(k):
            peg.run(ltp=ltp1)
    assert peg.broker.order_place.call_count == 2
    assert peg.broker.order_cancel.call_count == 1


def test_peg_sequential_dont_execute_after_time2(sequential_peg):
    peg = sequential_peg
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    k = known.add(seconds=60)
    with pendulum.test(k):
        peg.run(ltp=ltp1)
    assert peg.broker.order_place.call_count == 1
    assert peg.broker.order_cancel.call_count == 0


def test_peg_sequential_modify_after_time(sequential_peg):
    peg = sequential_peg
    for order in peg.orders:
        order.convert_to_market_after_expiry = True
        order.cancel_after_expiry = False
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    for i in range(30):
        k = known.add(seconds=i)
        with pendulum.test(k):
            peg.run(ltp=ltp1)
            if i == 3:
                peg.orders[0].update({"filled_quantity": 10})
            if i == 10:
                peg.orders[1].update({"filled_quantity": 10})
            if i == 13:
                peg.orders[2].update({"filled_quantity": 10})
            if i == 27:
                peg.orders[3].update({"filled_quantity": 10})
    assert peg.broker.order_place.call_count == 4
    assert peg.broker.order_modify.call_count == 4


def test_peg_sequential_modify_after_time2(sequential_peg):
    peg = sequential_peg
    peg.duration = 5
    peg.peg_every = 3
    for order in peg.orders:
        order.convert_to_market_after_expiry = True
        order.cancel_after_expiry = False
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    for i in range(25):
        k = known.add(seconds=i)
        with pendulum.test(k):
            peg.run(ltp=ltp1)
            if i == 5:
                peg.orders[0].update({"filled_quantity": 10})
            if i == 10:
                peg.orders[1].update({"filled_quantity": 10})
            if i == 15:
                peg.orders[2].update({"filled_quantity": 10})
            if i == 20:
                peg.orders[3].update({"filled_quantity": 10})
    assert peg.broker.order_place.call_count == 4
    assert peg.broker.order_modify.call_count == 4


def test_mark_subsequent_orders_as_canceled(sequential_peg):
    peg = sequential_peg
    peg._mark_subsequent_orders_as_canceled()
    assert [order.status for order in peg.orders] == [None] * 4

    for order in peg.orders:
        order.status = None
    peg.orders[0].status = "COMPLETE"
    peg.orders[1].status = "COMPLETE"
    peg.orders[2].status = "REJECTED"
    peg._mark_subsequent_orders_as_canceled()
    assert [order.status for order in peg.orders] == [
        "COMPLETE",
        "COMPLETE",
        "REJECTED",
        "CANCELED",
    ]
    peg._mark_done()
    assert peg.done is True


def test_mark_subsequent_orders_as_canceled_complete(sequential_peg):
    peg = sequential_peg
    peg._mark_subsequent_orders_as_canceled()
    peg.orders[0].status = "CANCELED"
    peg._mark_subsequent_orders_as_canceled()
    assert [order.status for order in peg.orders] == [
        "CANCELED",
        "CANCELED",
        "CANCELED",
        "CANCELED",
    ]
    peg._mark_done()
    assert peg.done is True

    for order in peg.orders:
        order.status = "COMPLETE"
    peg._mark_subsequent_orders_as_canceled()
    assert [order.status for order in peg.orders] == [
        "COMPLETE",
        "COMPLETE",
        "COMPLETE",
        "COMPLETE",
    ]
    peg._mark_done()
    assert peg.done is True


def test_peg_sequential_skip_subsequent_if_failed(sequential_peg):
    peg = sequential_peg
    peg.skip_subsequent_if_failed = True
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    for i in range(5, 40):
        k = known.add(seconds=i)
        if i == 10:
            peg.orders[0].filled_quantity = 10
            peg.orders[0].status = "COMPLETE"
        if i > 20:
            peg.orders[1].status = "CANCELED"
        with pendulum.test(k):
            peg.run(ltp=ltp1)
    assert peg.broker.order_place.call_count == 2
    assert [order.status for order in peg.orders] == [
        "COMPLETE",
        "CANCELED",
        "CANCELED",
        "CANCELED",
    ]
    assert peg.done is True


def test_peg_sequential_order_place_order_args(order_list):
    order_list.append(Order(symbol="dow", side="buy", quantity=10))
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10099)
        broker.order_modify.side_effect = range(10000, 10099)
        with pendulum.test(known):
            peg = PegSequential(
                orders=order_list,
                broker=broker,
                order_args={"validity": "day", "exchange": "nfo"},
            )
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    for i in range(5, 40):
        k = known.add(seconds=i)
        if i == 10:
            peg.orders[0].filled_quantity = 10
            peg.orders[0].status = "COMPLETE"
        with pendulum.test(k):
            peg.run(ltp=ltp1)
    call_args = peg.broker.order_place.call_args_list
    assert call_args[0].kwargs == dict(
        symbol="AAPL",
        side="BUY",
        order_type="LIMIT",
        quantity=10,
        disclosed_quantity=0,
        trigger_price=0,
        price=None,
        exchange="nfo",
        validity="day",
    )


def test_peg_sequential_execute_all_order_args(order_list):
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10099)
        broker.order_modify.side_effect = range(10000, 10099)
        with pendulum.test(known):
            peg = PegSequential(
                orders=order_list,
                broker=broker,
                order_args={"validity": "day", "exchange": "nfo"},
            )
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    with pendulum.test(known):
        peg.execute_all()
    assert peg.broker.order_place.call_count == 3
    call_args = peg.broker.order_place.call_args_list
    assert call_args[1].kwargs == dict(
        symbol="GOOG",
        side="BUY",
        order_type="LIMIT",
        quantity=10,
        disclosed_quantity=0,
        trigger_price=0,
        price=None,
        exchange="nfo",
        validity="day",
    )


def test_peg_sequential_order_modify_args(order_list):
    order_list.append(Order(symbol="dow", side="buy", quantity=10))
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    with patch("omspy.brokers.zerodha.Zerodha") as broker:
        broker.order_place.side_effect = range(10000, 10099)
        broker.order_modify.side_effect = range(10000, 10099)
        with pendulum.test(known):
            peg = PegSequential(
                orders=order_list,
                broker=broker,
                order_args={"validity": "day", "exchange": "nfo"},
                modify_args={"tag": "website"},
            )
    known = pendulum.datetime(2022, 1, 1, 10, tz="local")
    ltp1 = dict(aapl=100, goog=200, amzn=300, dow=400)
    for i in range(5, 40):
        k = known.add(seconds=i)
        if i == 10:
            peg.orders[0].filled_quantity = 10
            peg.orders[0].status = "COMPLETE"
        with pendulum.test(k):
            peg.run(ltp=ltp1)
    call_args = peg.broker.order_modify.call_args_list
    assert call_args[0].kwargs == dict(
        order_id=10001,
        order_type="LIMIT",
        quantity=10,
        disclosed_quantity=0,
        trigger_price=0,
        price=200,
        tag="website",
    )
