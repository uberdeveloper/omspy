from pathlib import PurePath
from omspy.brokers.noren import *
from omspy.order import Order
import pytest
import yaml
import json
from unittest.mock import patch
import pendulum

DATA_ROOT = PurePath(__file__).parent.parent.parent / "tests" / "data"
BROKERS_ROOT = PurePath(__file__).parent


@pytest.fixture
def broker():
    noren = Noren("user_id", "password", "totpcode", "vendor_code", "app_key", "imei")
    with patch("omspy.brokers.noren.NorenApi") as mock_broker:
        noren.noren = mock_broker
    return noren


@pytest.fixture
def mod():
    YAML_PATH = PurePath(__file__).parent.parent.parent / "omspy"
    with open(YAML_PATH / "brokers" / "finvasia.yaml") as f:
        return yaml.safe_load(f)


def test_noren_base():
    base = BaseNoren(host="https://api.noren.com", websocket="wss://api.noren.com")
    assert base._NorenApi__service_config["host"] == "https://api.noren.com"
    assert base._NorenApi__service_config["websocket_endpoint"] == "wss://api.noren.com"


def test_noren_defaults():
    noren = Noren(
        user_id="user_id",
        password="password",
        totp="totp",
        vendor_code="vendor_code",
        app_key="app_key",
        imei="imei",
        host="https://api.noren.com",
        websocket="wss://api.noren.com",
    )
    assert noren._user_id == "user_id"
    assert noren._password == "password"
    assert noren._totp == "totp"
    assert noren._vendor_code == "vendor_code"
    assert noren._app_key == "app_key"
    assert noren._imei == "imei"


def test_login(broker):
    broker.login()
    broker.noren.login.assert_called_once()


def test_authenticate():
    # Patching with noren module
    with patch("omspy.brokers.noren.BaseNoren") as mock_broker:
        broker = Noren(
            "user_id", "password", "totpcode", "vendor_code", "app_key", "imei"
        )
        broker.authenticate()
        broker.noren.login.assert_called_once()


def test_get_order_type(broker):
    assert broker.get_order_type("limit") == "LMT"
    assert broker.get_order_type("SLM") == "SL-MKT"
    assert broker.get_order_type("STOP") == "MKT"
    assert broker.get_order_type("SLL") == "SL-LMT"
    assert broker.get_order_type("SLL") == "SL-LMT"
    assert broker.get_order_type("SL-L") == "SL-LMT"
    assert broker.get_order_type("SL-M") == "SL-MKT"


def test_order_place(broker):
    broker.order_place(symbol="reliance-eq", side="buy", quantity=1)
    broker.noren.place_order.assert_called_once()
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
    assert broker.noren.place_order.call_args.kwargs == order_args


def test_order_place_change_args(broker):
    broker.order_place(
        symbol="reliance-eq",
        side="buy",
        quantity=100,
        validity="DAY",
        order_type="limit",
        price=2100,
    )
    broker.noren.place_order.assert_called_once()
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
    assert broker.noren.place_order.call_args.kwargs == order_args


def test_order_place_mixed_args(broker):
    broker.order_place(
        symbol="reliance-eq",
        side="buy",
        quantity=100,
        validity="DAY",
        price_type="LMT",
        price=2100,
        disclosed_quantity=15,
        product_type="N",
    )
    broker.noren.place_order.assert_called_once()
    order_args = dict(
        buy_or_sell="B",
        product_type="N",
        exchange="NSE",
        tradingsymbol="RELIANCE-EQ",
        quantity=100,
        price_type="LMT",
        price=2100,
        retention="DAY",
        discloseqty=15,
    )
    assert broker.noren.place_order.call_args.kwargs == order_args


def test_modify_order(broker):
    broker.order_modify(symbol="RELIANCE-EQ", quantity=5, order_id=1234)
    broker.noren.modify_order.assert_called_once()
    order_args = dict(
        orderno=1234,
        tradingsymbol="RELIANCE-EQ",
        newquantity=5,
        newprice_type="MKT",
        exchange="NSE",
    )
    assert broker.noren.modify_order.call_args.kwargs == order_args


def test_modify_order_kwargs(broker):
    broker.order_modify(
        symbol="RELIANCE-EQ",
        quantity=5,
        order_id="1234",
        exchange="NSE",
        order_type="limit",
        price=2075,
    )
    broker.noren.modify_order.assert_called_once()
    order_args = dict(
        orderno="1234",
        tradingsymbol="RELIANCE-EQ",
        newquantity=5,
        newprice_type="LMT",
        exchange="NSE",
        newprice=2075,
    )
    assert broker.noren.modify_order.call_args.kwargs == order_args


def test_cancel_order(broker):
    broker.order_cancel(order_id=1234)
    broker.noren.cancel_order.assert_called_once()


def test_convert_symbol(broker):
    assert broker._convert_symbol("reliance", "RELIANCE-EQ")
    assert broker._convert_symbol("RELIANCE-EQ", "RELIANCE-EQ")
    assert broker._convert_symbol("reliance-eq", "RELIANCE-EQ")


def test_place_order_without_eq(broker):
    broker.order_place(symbol="RELIANCE", side="BUY", quantity=1)
    broker.noren.place_order.assert_called_once()
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
    assert broker.noren.place_order.call_args.kwargs == order_args
