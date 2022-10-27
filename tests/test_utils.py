import os
from pathlib import PurePath

from omspy.utils import *
from copy import deepcopy
import pytest
import pandas as pd
import itertools

DATA_ROOT = PurePath(__file__).parent.parent / "tests" / "data"


@pytest.fixture
def load_orders():
    records = (
        pd.read_csv(DATA_ROOT / "real_orders.csv")
        .sort_values(by="symbol")
        .to_dict(orient="records")
    )
    return [r for r in records if r["status"] not in ("CANCELED", "REJECTED")]


@pytest.fixture
def dict_for_filter():
    def f(it, n):
        return itertools.chain.from_iterable(itertools.repeat(it, n))

    A = f(["A", "B", "C"], 8)
    B = f([100, 200, 300, 400], 6)
    C = f([1, 2, 3, 4, 5, 6], 4)
    dct = [dict(x=x, y=y, z=z) for x, y, z in zip(A, B, C)]
    return dct


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


def test_empty_dict(dict_for_filter):
    assert dict_filter([]) == []


def test_identity_dict(dict_for_filter):
    dct = [{"a": 15}, {"a": 20}, {"a": 10}]
    assert dict_filter(dct) == dct


def test_simple_dict(dict_for_filter):
    dct = [{"a": 15}, {"a": 20}, {"a": 10}]
    assert dict_filter(dct, a=10) == [{"a": 10}]


def test_no_matching_dict(dict_for_filter):
    assert dict_filter(dict_for_filter, y=1500) == []
    assert dict_filter(dict_for_filter, m=10) == []


def test_filter_one(dict_for_filter):
    x = ["A"] * 8
    y = [100, 400, 300, 200, 100, 400, 300, 200]
    z = [1, 4, 1, 4, 1, 4, 1, 4]
    lst1 = [dict(x=a, y=b, z=c) for a, b, c in zip(x, y, z)]
    assert dict_filter(dict_for_filter, x="A") == lst1


def test_filter_two(dict_for_filter):
    x = ["B"] * 4
    y = [100, 300, 100, 300]
    z = [5] * 4
    lst1 = [dict(x=a, y=b, z=c) for a, b, c in zip(x, y, z)]
    assert dict_filter(dict_for_filter, z=5) == lst1


def test_multi_filter(dict_for_filter):
    lst1 = [{"x": "A", "y": 100, "z": 1}] * 2
    assert dict_filter(dict_for_filter, x="A", y=100) == lst1

    lst2 = [{"x": "B", "y": 300, "z": 5}] * 2
    assert dict_filter(dict_for_filter, x="B", y=300, z=5) == lst2
    assert dict_filter(dict_for_filter, x="B", y=300) == lst2


def test_tick():
    assert tick(112.71) == 112.7
    assert tick(112.73) == 112.75
    assert tick(1054.85, tick_size=0.1) == 1054.8
    assert tick(1054.851, tick_size=0.1) == 1054.9
    assert tick(104.73, 1) == 105
    assert tick(103.2856, 0.01) == 103.29
    assert tick(0.007814, 0.001) == 0.008
    assert tick(0.00003562, 0.000001) == 0.000036
    assert tick(0.000035617, 0.00000002) == 0.00003562


@pytest.mark.parametrize(
    "test_input,expected",
    [
        ((123.3, "B", 0.45, 2), 121.45),
        ((123.3, "B", 0.55, 5), 119.55),
        ((123.3, "B", 0.55, -5), 119.55),
        ((1074.85, "B", 0.11, 100), 999.11),
        ((123.3, "S", 0.45, 2), 124.55),
        ((123.3, "S", 0.55, 5), 125.45),
        ((123.3, "S", 0.55, -5), 125.45),
        ((1074.85, "S", 0.11, 100), 1100.89),
    ],
)
def test_stop_loss_step_decimal(test_input, expected):
    assert stop_loss_step_decimal(*test_input) == expected
