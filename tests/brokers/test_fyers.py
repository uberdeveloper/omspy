from pathlib import PurePath
from omspy.brokers.fyers import Fyers
from unittest.mock import patch, call
import pytest
import json
from copy import deepcopy

# @@@ assumption [add test case]: this file location change breaks below paths
DATA_ROOT = PurePath(__file__).parent.parent.parent / "tests" / "data"
with open(DATA_ROOT / "fyers.json") as f:
    mock_data = json.load(f)


@pytest.fixture
def mock_fyers():
    broker = Fyers("app_id", "secret", "user_id", "password", "pan")
    with patch("fyers_api.fyersModel.FyersModel") as mock:
        broker.fyers = mock
    return broker


def test_profile(mock_fyers):
    broker = mock_fyers
    broker.fyers.get_profile.return_value = mock_data.get("profile")
    profile = broker.profile
    broker.fyers.get_profile.assert_called_once()
    assert profile == mock_data.get("profile")


def test_funds(mock_fyers):
    broker = mock_fyers
    broker.fyers.funds.return_value = mock_data.get("funds")
    funds = broker.funds
    broker.fyers.funds.assert_called_once()
    assert funds == mock_data.get("funds")


def test_orders(mock_fyers):
    broker = mock_fyers
    broker.fyers.orderbook.return_value = mock_data.get("orders")
    orders = broker.orders
    broker.fyers.orderbook.assert_called_once()
    keys_in = [
        "order_id",
        "order_timestamp",
        "price",
        "quantity",
        "filled_quantity",
        "status",
        "exchange_order_id",
        "order_type",
    ]
    keys_not_in = [
        "id",
        "orderDateTime",
        "tradedPrice",
        "qty",
        "filledQty",
        "exchOrdId",
        "type",
    ]
    for order in orders:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in order
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in order


def test_orders_empty_orderbook(mock_fyers):
    broker = mock_fyers
    broker.fyers.orderbook.return_value = {}
    orders = broker.orders
    assert orders == [{}]


def test_orders_mappings(mock_fyers):
    # Test whether constants are matched correctly
    broker = mock_fyers
    broker.fyers.orderbook.return_value = mock_data.get("orders")
    orders = broker.orders
    assert orders[0]["status"] == "COMPLETE"
    assert orders[0]["exchange"] == "NSE"
    assert orders[0]["side"] == "buy"
    assert orders[0]["order_type"] == "MARKET"
    assert orders[1]["order_type"] == "LIMIT"
    assert orders[1]["side"] == "buy"
    assert orders[1]["status"] == "COMPLETE"


def test_positions(mock_fyers):
    broker = mock_fyers
    broker.fyers.positions.return_value = mock_data.get("positions")
    positions = broker.positions
    broker.fyers.positions.assert_called_once()
    keys_in = ["quantity", "average_price"]
    keys_not_in = ["netQty", "avgPrice"]
    for position in positions:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in position
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in position


def test_positions_mappings(mock_fyers):
    # Test whether constants are matched correctly
    broker = mock_fyers
    broker.fyers.positions.return_value = mock_data.get("positions")
    positions = broker.positions
    assert positions[0]["side"] == "buy"
    assert positions[0]["quantity"] == 1
    assert positions[0]["average_price"] == 72256


def test_trades(mock_fyers):
    broker = mock_fyers
    broker.fyers.trades.return_value = mock_data.get("trades")
    trades = broker.trades
    broker.fyers.tradebook.assert_called_once()
    keys_in = ["trade_id", "quantity", "order_id"]
    keys_not_in = ["id", "tradedQty", "orderNumber"]
    for trade in trades:
        # assert keys are in dictionary, overriden keys
        for key in keys_in:
            assert key in trade
        # assert keys not in dictionary, original keys
        for key in keys_not_in:
            assert key not in trade


def test_trades_mappings(mock_fyers):
    # Test whether constants are matched correctly
    broker = mock_fyers
    broker.fyers.tradebook.return_value = mock_data.get("trades")
    trades = broker.trades
    assert trades[0]["side"] == "buy"
    assert trades[1]["exchange"] == "NSE"
    assert trades[1]["segment"] == "capital"


def test_order_place(mock_fyers):
    broker = mock_fyers
    broker.fyers.place_order.return_value = mock_data.get("place_order")
    broker.order_place(symbol="goog", side="buy")
    broker.fyers.place_order.assert_called_once()
    kwargs = {"symbol": "goog", "side": 1, "qty": 1, "type": 2}
    assert broker.fyers.place_order.call_args_list[-1] == call(kwargs)


def test_order_place_arguments(mock_fyers):
    broker = mock_fyers
    broker.fyers.place_order.return_value = mock_data.get("place_order")
    broker.order_place(
        symbol="goog", side="sell", order_type="LIMIT", quantity=10, price=380
    )
    broker.fyers.place_order.assert_called_once()
    kwargs = {"symbol": "goog", "side": -1, "qty": 10, "type": 1, "limitPrice": 380}


def test_order_place_kwargs(mock_fyers):
    broker = mock_fyers
    broker.fyers.place_order.return_value = mock_data.get("place_order")
    broker.order_place(
        symbol="goog",
        side="sell",
        order_type="SL-M",
        quantity=50,
        price=380,
        trigger_price=379,
        disclosed_quantity=10,
    )
    broker.fyers.place_order.assert_called_once()
    kwargs = {
        "symbol": "goog",
        "side": -1,
        "qty": 50,
        "type": 3,
        "limitPrice": 380,
        "stopPrice": 379,
        "disclosedQty": 10,
    }
    assert broker.fyers.place_order.call_args_list[-1] == call(kwargs)


def test_modify_order(mock_fyers):
    broker = mock_fyers
    broker.fyers.modify_order.return_value = mock_data.get("modify_order")
    order_id = "8102710298291"
    broker.order_modify(order_id=order_id, price=150)
    broker.fyers.modify_order.assert_called_once()
    kwargs = {"id": "8102710298291", "limitPrice": 150}
    assert broker.fyers.modify_order.call_args_list[-1] == call(kwargs)


def test_modify_order_kwargs(mock_fyers):
    broker = mock_fyers
    broker.fyers.modify_order.return_value = mock_data.get("modify_order")
    order_id = "8102710298291"
    broker.order_modify(
        order_id=order_id,
        price=150,
        trigger_price=151,
        order_type="market",
        quantity=10,
    )
    broker.fyers.modify_order.assert_called_once()
    kwargs = {
        "id": "8102710298291",
        "limitPrice": 150,
        "stopLoss": 151,
        "type": 2,
        "qty": 10,
    }
    assert broker.fyers.modify_order.call_args_list[-1] == call(kwargs)


def test_cancel_order(mock_fyers):
    broker = mock_fyers
    broker.fyers.cancel_order.return_value = mock_data.get("cancel_order")
    broker.order_cancel("808058117761")
    broker.fyers.cancel_order.assert_called_once()
    broker.fyers.cancel_order.assert_called_with({"id": "808058117761"})
