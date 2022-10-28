from pathlib import PurePath

from omspy.brokers.zerodha import Zerodha
from unittest.mock import patch, call
import pytest
import json
from copy import deepcopy

# @@@ assumption [add test case]: this file location change breaks below paths
KITE_CONNECT_ROOT = (
    PurePath(__file__).parent.parent.parent / "tests" / "data" / "kiteconnect"
)


@pytest.fixture
def mock_kite():
    broker = Zerodha("api_key", "secret", "user_id", "password", "pin")
    with patch("kiteconnect.KiteConnect") as mock:
        broker.kite = mock
    return broker


def test_profile(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "profile.json") as f:
        mock_data = json.load(f)
    broker.kite.profile.return_value = mock_data
    profile = broker.profile
    broker.kite.profile.assert_called_once()
    assert profile == mock_data


def test_orders(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "orders.json") as f:
        mock_data = json.load(f).get("data")
    broker.kite.orders.return_value = mock_data
    orders = broker.orders
    broker.kite.orders.assert_called_once()
    keys_in = [
        "side",
        "symbol",
        "order_id",
        "order_timestamp",
        "price",
        "quantity",
        "filled_quantity",
        "status",
        "exchange_order_id",
        "order_type",
    ]
    keys_not_in = ["transaction_type", "tradingsymbol"]
    for order in orders:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in order
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in order


def test_orders_empty_orderbook(mock_kite):
    broker = mock_kite
    broker.kite.orders.return_value = {}
    orders = broker.orders
    assert orders == [{}]


def test_trades(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "trades.json") as f:
        mock_data = json.load(f).get("data")
    broker.kite.trades.return_value = mock_data
    trades = broker.trades
    broker.kite.trades.assert_called_once()
    keys_in = ["trade_id", "symbol"]
    keys_not_in = ["tradingsymbol"]
    for trade in trades:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in trade
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in trade


def test_positions(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "positions.json") as f:
        mock_data = json.load(f).get("data")
    broker.kite.positions.return_value = mock_data
    positions = broker.positions
    broker.kite.positions.assert_called_once()
    keys_in = ["symbol"]
    keys_not_in = ["tradingsymbol"]
    for position in positions:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in position
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in position


def test_positions_side(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "positions.json") as f:
        mock_data = json.load(f).get("data")
    broker.kite.positions.return_value = mock_data
    positions = broker.positions
    assert positions[0]["side"] == "SELL"
    assert positions[1]["side"] == "BUY"
    assert positions[2]["side"] == "SELL"


def test_order_place(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "order_response.json") as f:
        mock_data = json.load(f)
    broker.kite.place_order.return_value = mock_data
    broker.order_place(symbol="goog", side="BUY", quantity=1, order_type="MARKET")
    broker.kite.place_order.assert_called_once()
    kwargs = {
        "tradingsymbol": "goog",
        "transaction_type": "BUY",
        "quantity": 1,
        "order_type": "MARKET",
        "variety": "regular",
        "validity": "DAY",
        "product": "MIS",
        "exchange": "NSE",
    }
    assert broker.kite.place_order.call_args_list[-1] == call(**kwargs)


def test_order_place_kwargs(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "order_response.json") as f:
        mock_data = json.load(f)
    broker.kite.place_order.return_value = mock_data
    broker.order_place(
        symbol="goog",
        side="BUY",
        quantity=1,
        order_type="MARKET",
        variety="amo",
        exchange="nse",
        validity="day",
        product="cnc",
    )
    broker.kite.place_order.assert_called_once()
    kwargs = {
        "tradingsymbol": "goog",
        "transaction_type": "BUY",
        "quantity": 1,
        "order_type": "MARKET",
        "variety": "amo",
        "exchange": "nse",
        "validity": "day",
        "product": "cnc",
    }
    assert broker.kite.place_order.call_args_list[-1] == call(**kwargs)


def test_order_modify(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "order_response.json") as f:
        mock_data = json.load(f)
    broker.kite.modify_order.return_value = mock_data
    broker.order_modify(order_id="abcde12345", quantity=100, order_type="market")
    broker.kite.modify_order.assert_called_once()
    kwargs = {
        "order_id": "abcde12345",
        "quantity": 100,
        "order_type": "market",
        "variety": "regular",
    }
    assert broker.kite.modify_order.call_args_list[-1] == call(**kwargs)


def test_order_modify_return_error(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "order_response.json") as f:
        mock_data = json.load(f)
    broker.kite.modify_order.return_value = mock_data
    response = broker.order_modify(quantity=100, order_type="market")
    broker.kite.modify_order.assert_not_called()
    kwargs = {"order_id": "abcde12345", "quantity": 100, "order_type": "market"}
    assert response == {"error": "No order_id"}


def test_order_cancel(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "order_response.json") as f:
        mock_data = json.load(f)
    broker.kite.cancel_order.return_value = mock_data
    broker.order_cancel(order_id="abcde12345", variety="regular")
    broker.kite.cancel_order.assert_called_once()
    kwargs = {"order_id": "abcde12345", "variety": "regular"}
    assert broker.kite.cancel_order.call_args_list[-1] == call(**kwargs)


def test_order_cancel_return_error(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "order_response.json") as f:
        mock_data = json.load(f)
    broker.kite.cancel_order.return_value = mock_data
    response = broker.order_cancel(order_type="market")
    broker.kite.cancel_order.assert_not_called()
    assert response == {"error": "No order_id"}


def test_close_all_positions(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "positions.json") as f:
        mock_data = json.load(f).get("data")
    broker.kite.positions.return_value = mock_data
    broker.close_all_positions(keys_to_copy=("exchange", "product", "product"))
    assert broker.kite.place_order.call_count == 2
    call_args = [
        dict(
            tradingsymbol="GOLDGUINEA17DECFUT",
            order_type="MARKET",
            quantity=3,
            transaction_type="buy",
            variety="regular",
            product="NRML",
            validity="DAY",
            exchange="MCX",
        ),
        dict(
            tradingsymbol="LEADMINI17DECFUT",
            order_type="MARKET",
            quantity=1,
            transaction_type="sell",
            variety="regular",
            product="NRML",
            validity="DAY",
            exchange="MCX",
        ),
    ]
    order_args = broker.kite.place_order.call_args_list
    print(order_args)
    print(call_args)
    assert order_args[0] == call(**call_args[0])
    assert order_args[1] == call(**call_args[1])


def test_cancel_all_orders(mock_kite):
    broker = mock_kite
    with open(KITE_CONNECT_ROOT / "orders.json") as f:
        mock_data = json.load(f).get("data")
        mock_data[3]["status"] = "PENDING"
    broker.kite.orders.return_value = mock_data
    broker.cancel_all_orders(
        keys_to_copy=("product", "instrument_token"), keys_to_add={"variety": "regular"}
    )
    assert broker.kite.cancel_order.call_count == 1
    call_args = [
        dict(
            order_id="100000000000000",
            instrument_token=412675,
            product="NRML",
            variety="regular",
        ),
        dict(
            order_id="700000000000000",
            instrument_token=58424839,
            product="NRML",
            variety="regular",
        ),
    ]
    order_args = broker.kite.cancel_order.call_args_list
    assert order_args[0] == call(**call_args[1])


def test_cancel_order(mock_kite):
    broker = mock_kite
    broker.order_cancel(order_id="123456")
    call_args = dict({"order_id": "123456", "variety": "regular"})
    broker.kite.cancel_order.assert_called_once()
    order_args = broker.kite.cancel_order.call_args_list
    assert order_args[0] == call(**call_args)
