from omspy.brokers.finvasia import *
import pytest
from unittest.mock import patch


@pytest.fixture
def broker():
    finvasia = Finvasia("user_id", "password", "pin", "vendor_code", "app_key", "imei")
    with patch("omspy.brokers.api_helper.ShoonyaApiPy") as mock_broker:
        finvasia.finvasia = mock_broker
    return finvasia


def test_defaults(broker):
    assert broker._user_id == "user_id"
    assert broker._password == "password"
    assert broker._pin == "pin"
    assert broker._vendor_code == "vendor_code"
    assert broker._app_key == "app_key"
    assert broker._imei == "imei"
    assert hasattr(broker, "finvasia")


def test_login(broker):
    broker.login()
    broker.finvasia.login.assert_called_once()

def test_authenticate(broker):
    broker.authenticate()
    broker.finvasia.login.assert_called_once()

def test_get_order_type(broker):
    assert broker.get_order_type("limit") == "LMT"
    assert broker.get_order_type("SLM") == "SL-MKT"
    assert broker.get_order_type("STOP") == "MKT"


def test_place_order(broker):
    broker.order_place(symbol="reliance-eq", side="buy", quantity=1)
    broker.finvasia.place_order.assert_called_once()
    order_args = dict(
        buy_or_sell="B",
        product_type="I",
        exchange="NSE",
        tradingsymbol="RELIANCE-EQ",
        quantity=1,
        price_type="MKT",
        retention="DAY",
        discloseqty=0,
    )
    assert broker.finvasia.place_order.call_args.kwargs == order_args


def test_place_order_change_args(broker):
    broker.order_place(
        symbol="reliance-eq",
        side="buy",
        quantity=100,
        validity="DAY",
        order_type="limit",
        price=2100,
    )
    broker.finvasia.place_order.assert_called_once()
    order_args = dict(
        buy_or_sell="B",
        product_type="I",
        exchange="NSE",
        tradingsymbol="RELIANCE-EQ",
        quantity=100,
        price_type="LMT",
        price=2100,
        retention="DAY",
        discloseqty=0,
    )
    assert broker.finvasia.place_order.call_args.kwargs == order_args


def test_place_order_mixed_args(broker):
    broker.order_place(
        symbol="reliance-eq",
        side="buy",
        quantity=100,
        validity="DAY",
        price_type="LMT",
        price=2100,
        disclosed_quantity=15,
    )
    broker.finvasia.place_order.assert_called_once()
    order_args = dict(
        buy_or_sell="B",
        product_type="I",
        exchange="NSE",
        tradingsymbol="RELIANCE-EQ",
        quantity=100,
        price_type="LMT",
        price=2100,
        retention="DAY",
        discloseqty=15,
    )
    assert broker.finvasia.place_order.call_args.kwargs == order_args


def test_modify_order(broker):
    broker.order_modify(symbol="RELIANCE-EQ", quantity=5, order_id=1234)
    broker.finvasia.modify_order.assert_called_once()
    order_args = dict(
        orderno=1234,
        tradingsymbol="RELIANCE-EQ",
        newquantity=5,
        newprice_type="MKT",
        exchange="NSE",
    )
    assert broker.finvasia.modify_order.call_args.kwargs == order_args


def test_modify_order_kwargs(broker):
    broker.order_modify(
        symbol="RELIANCE-EQ",
        quantity=5,
        order_id="1234",
        exchange="NSE",
        order_type="limit",
        price=2075,
    )
    broker.finvasia.modify_order.assert_called_once()
    order_args = dict(
        orderno="1234",
        tradingsymbol="RELIANCE-EQ",
        newquantity=5,
        newprice_type="LMT",
        exchange="NSE",
        newprice=2075,
    )
    assert broker.finvasia.modify_order.call_args.kwargs == order_args


def test_cancel_order(broker):
    broker.order_cancel(order_id=1234)
    broker.finvasia.cancel_order.assert_called_once()


def test_convert_symbol(broker):
    assert broker._convert_symbol("reliance", "RELIANCE-EQ")
    assert broker._convert_symbol("RELIANCE-EQ", "RELIANCE-EQ")
    assert broker._convert_symbol("reliance-eq", "RELIANCE-EQ")


def test_place_order_without_eq(broker):
    broker.order_place(symbol="RELIANCE", side="BUY", quantity=1)
    broker.finvasia.place_order.assert_called_once()
    order_args = dict(
        buy_or_sell="B",
        product_type="I",
        exchange="NSE",
        tradingsymbol="RELIANCE-EQ",
        quantity=1,
        price_type="MKT",
        retention="DAY",
        discloseqty=0,
    )
    assert broker.finvasia.place_order.call_args.kwargs == order_args
