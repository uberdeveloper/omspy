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


def test_basic_peg():
    peg = BasicPeg(symbol="aapl", side="buy", quantity=100, broker=Paper())
    assert peg.count == 1
    assert peg.orders[0].order_type == "LIMIT"
    assert peg.ltp["aapl"] == 0.0


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


@patch("omspy.brokers.zerodha.Zerodha")
def test_existing_peg_run(broker):
    known = pendulum.datetime(2022, 4, 1, 10, 0)
    order = Order(symbol="amzn", quantity=20, side="buy")
    with pendulum.test(known):
        peg = PegExisting(order=order, broker=broker)
        peg.execute(broker=broker)
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
        peg.execute(broker=broker)
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
        peg.execute(broker=broker)
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
        peg.execute(broker=broker)
        broker.order_place.assert_called_once()
    known = known.add(seconds=4)
    with pendulum.test(known):
        order.filled_quantity = 200
        peg.run(ltp=252)
        broker.order_modify.assert_not_called()
        assert peg.done is True
