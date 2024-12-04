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
def simple():
    return Order(
        symbol="aapl",
        side="buy",
        quantity=100,
        order_id="202212010001708",
        order_type="limit",
        price=238,
    )


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


def test_orders(broker, mod):
    with open(DATA_ROOT / "finvasia" / "orders.json", "r") as f:
        orders = json.load(f)
    broker.noren.get_order_book.return_value = orders
    fetched = broker.orders
    keys = mod["orders"]
    # Testing original keys are not in modified dataframe
    for order in fetched:
        for k, v in keys.items():
            assert k not in order


def test_trades(broker, mod):
    with open(DATA_ROOT / "finvasia" / "trades.json", "r") as f:
        trades = json.load(f)
    broker.noren.get_trade_book.return_value = trades
    fetched = broker.trades
    keys = mod["trades"]
    # Testing original keys are not in modified dataframe
    for trade in fetched:
        for k, v in keys.items():
            assert k not in trade
            assert v in trade


def test_positions(broker, mod):
    with open(DATA_ROOT / "finvasia" / "positions.json", "r") as f:
        positions = json.load(f)
    broker.noren.get_positions.return_value = positions
    fetched = broker.positions
    keys = mod["positions"]
    # Testing original keys are not in modified dataframe
    for order in fetched:
        for k, v in keys.items():
            assert k not in order
            assert v in order


def test_orders_type_conversion(broker):
    with open(DATA_ROOT / "finvasia" / "orders.json", "r") as f:
        orders = json.load(f)
    broker.noren.get_order_book.return_value = orders
    fetched = broker.orders
    expected = (
        47.5,
        155.9,
        113.65,
        0,
        113.4,
        0,
        156.45,
        0,
        47.3,
    )
    expected_rprc = (
        47.5,
        155.9,
        113.65,
        118,
        113.4,
        160,
        156.45,
        50,
        47.3,
    )
    for f, e, r in zip(fetched, expected, expected_rprc):
        assert f["quantity"] == 1
        assert f["average_price"] == e
        assert f["rprc"] == r
        assert type(f["quantity"]) == int
        assert type(f["filled_quantity"]) == int
        assert type(f["average_price"]) == float
        assert type(f["trigger_price"]) == float
        assert type(f["price"]) == float
        assert type(f["rprc"]) == float


def test_positions_type_conversion(broker):
    with open(DATA_ROOT / "finvasia" / "positions.json", "r") as f:
        positions = json.load(f)
    broker.noren.get_positions.return_value = positions
    fetched = broker.positions
    for pos in fetched:
        assert pos["quantity"] == 0
        assert type(pos["quantity"]) == int
        assert type(pos["daybuyqty"]) == int
        assert type(pos["daysellqty"]) == int
        assert type(pos["cfbuyqty"]) == int
        assert type(pos["cfsellqty"]) == int
        assert type(pos["openbuyqty"]) == int
        assert type(pos["opensellqty"]) == int
        assert type(pos["day_buy_value"]) == float
        assert type(pos["day_sell_value"]) == float
        assert type(pos["last_price"]) == float
        assert type(pos["rpnl"]) == float
        assert type(pos["dayavgprc"]) == float
        assert type(pos["daybuyavgprc"]) == float
        assert type(pos["daysellavgprc"]) == float
        assert type(pos["urmtom"]) == float


def test_trades_type_conversion(broker):
    with open(DATA_ROOT / "finvasia" / "trades.json", "r") as f:
        trades = json.load(f)
    broker.noren.get_trade_book.return_value = trades
    expected = (47.5, 155.9, 113.65, 113.4, 156.45, 47.3)
    fetched = broker.trades
    for f, e in zip(fetched, expected):
        assert f["price"] == e
        assert type(f["filled_quantity"]) == int
        assert type(f["qty"]) == int
        assert type(f["fillshares"]) == int
        assert type(f["prc"]) == float
        assert type(f["price"]) == float


def test_orders_timestamp_conversion(broker):
    with open(DATA_ROOT / "finvasia" / "orders.json", "r") as f:
        orders = json.load(f)
        broker.noren.get_order_book.return_value = orders
        fetched = broker.orders
        ts_array = [
            (2022, 6, 14, 15, 6, 38),
            (2022, 6, 14, 15, 6, 25),
            (2022, 6, 14, 15, 6, 7),
            (2022, 6, 14, 14, 54, 36),
            (2022, 6, 14, 14, 37, 55),
            (2022, 6, 14, 14, 54, 36),
            (2022, 6, 14, 14, 37, 55),
            (2022, 6, 14, 14, 54, 36),
            (2022, 6, 14, 14, 37, 54),
        ]
        expected_timestamp = [
            pendulum.datetime(*ts, tz="Asia/Kolkata") for ts in ts_array
        ]
        for order, ts in zip(orders, expected_timestamp):
            assert order["exchange_timestamp"] == str(ts)
            assert order["broker_timestamp"] == str(ts)


def test_place_order_different_exchange(broker):
    broker.order_place(symbol="RELIANCE", side="BUY", quantity=1, exchange="NFO")
    broker.noren.place_order.assert_called_once()
    order_args = dict(
        buy_or_sell="B",
        product_type="I",
        exchange="NFO",
        tradingsymbol="RELIANCE",
        quantity=1,
        price_type="MKT",
        retention="DAY",
        discloseqty=0,
    )
    assert broker.noren.place_order.call_args.kwargs == order_args


def test_place_order_different_exchange(broker):
    broker.order_place(symbol="RELIANCE", side="BUY", quantity=1, exchange="NFO")
    broker.noren.place_order.assert_called_once()
    order_args = dict(
        buy_or_sell="B",
        product_type="I",
        exchange="NFO",
        tradingsymbol="RELIANCE",
        quantity=1,
        price_type="MKT",
        retention="DAY",
        discloseqty=0,
    )
    assert broker.noren.place_order.call_args.kwargs == order_args


def test_order_modify_from_order_attribs_to_copy(simple, broker):
    simple.modify(price=230, quantity=225, broker=broker, attribs_to_copy=("symbol",))
    broker.noren.modify_order.assert_called_once()
    order_args = dict(
        orderno="202212010001708",
        tradingsymbol="AAPL-EQ",
        newquantity=225,
        newprice=230,
        newprice_type="LMT",
        newtrigger_price=0,
        exchange="NSE",
    )
    assert broker.noren.modify_order.call_args.kwargs == order_args


def test_order_modify_from_order_attribs_to_copy_from_broker(simple, broker):
    simple.modify(price=230, quantity=225, broker=broker)
    broker.noren.modify_order.assert_called_once()
    order_args = dict(
        orderno="202212010001708",
        tradingsymbol="AAPL-EQ",
        newquantity=225,
        newprice=230,
        newprice_type="LMT",
        newtrigger_price=0,
        exchange="NSE",
    )
    assert broker.noren.modify_order.call_args.kwargs == order_args
