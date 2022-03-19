from omspy.orders.peg import *
import pytest
from omspy.brokers.paper import Paper
from omspy.order import create_db
import pendulum
from unittest.mock import patch, call


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
        peg = PegMarket(symbol="aapl", side="buy", quantity=100, broker=Paper(),connection=connection)
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
            exchange='nse',
            client_id='ab1111',
            order_type='MARKET'
        )
        assert peg.num_pegs == 0
        assert peg._max_pegs == 7
        assert peg._expire_at == pendulum.datetime(
            2022, 1, 1, 10, minute=8, second=15, tz="Asia/Kolkata"
        )
        assert peg.next_peg == pendulum.datetime(
            2022, 1, 1, 10, minute=6, second=5, tz="Asia/Kolkata"
        )
        assert peg.orders[0].exchange == 'nse'
        assert peg.orders[0].client_id == 'ab1111'
        assert peg.orders[0].order_type == 'LIMIT'

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
