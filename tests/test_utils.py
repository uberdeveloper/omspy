from omspy.utils import *
from copy import deepcopy
import pytest
import pandas as pd


@pytest.fixture
def load_orders():
    records = (
        pd.read_csv("tests/data/real_orders.csv")
        .sort_values(by="symbol")
        .to_dict(orient="records")
    )
    return [r for r in records if r["status"] not in ("CANCELED", "REJECTED")]


def test_create_basic_positions_from_orders_dict_keys(load_orders):
    assert len(load_orders) == 27
    positions = create_basic_positions_from_orders_dict(load_orders)
    symbols = [
        "BHARATFORG",
        "CANBK",
        "IRCTC",
        "LICHSGFIN",
        "MANAPPURAM",
        "MINDTREE",
        "NIFTY2221017450PE",
        "NIFTY22FEB17400CE",
        "PAGEIND",
        "PETRONET",
        "SRF",
    ]
    for s in symbols:
        assert s in positions


def test_create_basic_positions_from_orders_dict_quantity(load_orders):
    positions = create_basic_positions_from_orders_dict(load_orders)
    symbols = [
        "BHARATFORG",
        "CANBK",
        "IRCTC",
        "LICHSGFIN",
        "MANAPPURAM",
        "MINDTREE",
        "NIFTY2221017450PE",
        "NIFTY22FEB17400CE",
        "PAGEIND",
        "PETRONET",
        "SRF",
    ]

    qty = [160, 429, 136, 286, 733, 28, 50, 50, 2, 540, 46]
    for s, qty in zip(symbols, qty):
        pos = positions.get(s)
        assert pos.buy_quantity == pos.sell_quantity == qty


def test_create_basic_positions_from_orders_dict_value(load_orders):
    positions = create_basic_positions_from_orders_dict(load_orders)
    symbols = [
        "BHARATFORG",
        "CANBK",
        "IRCTC",
        "LICHSGFIN",
        "MANAPPURAM",
        "MINDTREE",
        "NIFTY2221017450PE",
        "NIFTY22FEB17400CE",
        "PAGEIND",
        "PETRONET",
        "SRF",
    ]
    buy_value = [
        119792,
        111540,
        115600,
        112154.9,
        116107.2,
        111885.2,
        4715,
        12375,
        84918,
        117759.05,
        118803.75,
    ]
    sell_value = [
        117064.05,
        112097.7,
        116817.2,
        111840.3,
        117353.3,
        110038.6,
        4122.5,
        13650,
        82797.9,
        117315,
        117293.1,
    ]

    for s, bv in zip(symbols, buy_value):
        pos = positions.get(s)
        assert round(pos.buy_value, 2) == round(bv, 2)

    for s, sv in zip(symbols, sell_value):
        pos = positions.get(s)
        assert round(pos.sell_value, 2) == round(sv, 2)


def test_create_basic_positions_from_orders_dict_qty_non_match(load_orders):
    orders = load_orders[:3][:]
    del orders[1]
    positions = create_basic_positions_from_orders_dict(orders)
    pos = positions["BHARATFORG"]
    print(pos)
    assert pos.sell_quantity == 153
    assert pos.sell_value == 111934.8
    assert pos.average_sell_value == 731.6

    # Modifying the order
    o = deepcopy(orders[0])
    o["quantity"] = 130
    o["price"] = 0
    o["trigger_price"] = 728
    o["average_price"] = 0
    orders.append(o)
    positions = create_basic_positions_from_orders_dict(orders)
    pos = positions["BHARATFORG"]
    assert pos.buy_quantity == 290
    assert pos.buy_value == 214432
    assert round(pos.average_buy_value, 2) == 739.42
