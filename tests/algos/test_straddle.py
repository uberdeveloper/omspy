import pytest
from omspy.algos.straddle import *
from pydantic import ValidationError


@pytest.fixture
def simple_straddle():
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        return ShortStraddle(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
            symbols=("nifty22may17500ce", "nifty22may17500pe"),
        )


@pytest.fixture
def price_straddle():
    known = pendulum.datetime(2022, 1, 1, tz="local")
    with pendulum.test(known):
        return ShortStraddle(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10, tz="local"),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10, tz="local"),
            symbols=("nifty22may17500ce", "nifty22may17500pe"),
            limit_price=(200, 210.4),
            trigger_price=(240, 268),
            stop_price=(242, 270),
            quantity=50,
        )


def test_base_strategy_defaults():
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        base = BaseStrategy(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
        )
        assert base.timer.start_time == pendulum.datetime(2022, 1, 1, 10, 10)
        assert base.timer.end_time == pendulum.datetime(2022, 1, 1, 15, 10)
        assert base._pegs == []


def test_base_strategy_end_time_less_than_start_time():
    with pytest.raises(ValidationError):
        base = BaseStrategy(
            start_time=pendulum.datetime(2022, 1, 2, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
        )


def test_base_strategy_start_time_less_than_now():
    known = pendulum.datetime(2022, 1, 4, 10, 15)
    with pendulum.test(known):
        with pytest.raises(ValidationError):
            base = BaseStrategy(
                start_time=pendulum.datetime(2022, 1, 4, 10, 12),
                end_time=pendulum.datetime(2022, 1, 4, 10, 20),
            )


def test_base_strategy_time():
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        base = BaseStrategy(
            start_time=pendulum.datetime(2022, 1, 1, 10, 10),
            end_time=pendulum.datetime(2022, 1, 1, 15, 10),
            timezone="Europe/Paris",
        )
        assert base.timer.start_time == base.start_time
        assert base.timer.end_time == base.end_time


def test_short_straddle_defaults(simple_straddle):
    assert simple_straddle.start_time == pendulum.datetime(2022, 1, 1, 10, 10)
    assert simple_straddle.symbols == ("nifty22may17500ce", "nifty22may17500pe")
    assert simple_straddle.order is not None
    assert list(simple_straddle._order_map.keys()) == [
        "entry1",
        "exit1",
        "entry2",
        "exit2",
    ]
    assert simple_straddle._pegs == []
    assert simple_straddle.ltp == {"nifty22may17500ce": 0, "nifty22may17500pe": 0}


def test_short_straddle_create_order_defaults(simple_straddle):
    straddle = simple_straddle
    assert straddle.order.count == 0
    # Should create order only once despite calling many times
    straddle.create_order()
    straddle.create_order()
    straddle.create_order()
    assert straddle.order.count == 4
    assert [x.side for x in straddle.order.orders] == ["sell", "sell", "buy", "buy"]
    assert [x.order_type for x in straddle.order.orders] == [
        "MARKET",
        "MARKET",
        "SL",
        "SL",
    ]


def test_short_straddle_limit_prices(price_straddle):
    straddle = price_straddle
    order = straddle.create_order()
    assert order.orders[0].price == 200
    assert order.orders[1].price == 210.4
    assert order.orders[2].trigger_price == 240
    assert order.orders[3].trigger_price == 268
    assert order.orders[2].price == 242
    assert order.orders[3].price == 270


def test_short_straddle_get_order(simple_straddle):
    straddle = simple_straddle
    assert straddle.order.count == 0
    assert straddle.get_order("entry1") is None
    straddle.create_order()
    assert straddle.get_order("entry1") == straddle._order.orders[0]
    assert straddle.get_order("exit1") == straddle._order.orders[2]
    assert straddle.get_order("entry2") == straddle._order.orders[1]
    assert straddle.get_order("exit2") == straddle._order.orders[3]
    assert straddle.get_order("exit5") is None


def test_check_orders_complete(simple_straddle):
    straddle = simple_straddle
    straddle.create_order()
    order1 = straddle.order.orders[0]
    order2 = straddle.order.orders[2]
    check = straddle._check_orders_complete(order1, order2)
    assert check is False
    order1.status = order2.status = "COMPLETE"
    check = straddle._check_orders_complete(order1, order2)
    assert check is True
    order1.status = "REJECTED"
    check = straddle._check_orders_complete(order1, order2)
    assert check is False
    order2.status = "CANCELED"
    check = straddle._check_orders_complete(order1, order2)
    assert check is True


def test_is_first_leg_complete(simple_straddle):
    straddle = simple_straddle
    assert straddle.is_first_leg_complete is False
    straddle.create_order()
    assert straddle.is_first_leg_complete is False
    straddle.order.orders[0].status = "COMPLETE"
    straddle.order.orders[2].status = "COMPLETE"
    assert straddle.is_first_leg_complete is True


def test_is_second_leg_complete(simple_straddle):
    straddle = simple_straddle
    assert straddle.is_second_leg_complete is False
    straddle.create_order()
    assert straddle.is_second_leg_complete is False
    straddle.order.orders[1].status = "REJECTED"
    straddle.order.orders[3].status = "REJECTED"
    assert straddle.is_second_leg_complete is True


def test_check_sell_without_buy(simple_straddle):
    straddle = simple_straddle
    straddle.create_order()
    one = straddle.order.orders[0]
    two = straddle.order.orders[2]
    assert straddle._check_sell_without_buy(one, two) is False
    one.status = "COMPLETE"
    assert straddle._check_sell_without_buy(one, two) is False
    one.status = two.status = "PENDING"
    assert straddle._check_sell_without_buy(one, two) is False
    one.status, two.status = "REJECTED", "COMPLETE"
    assert straddle._check_sell_without_buy(one, two) is False
    one.status, two.status = "COMPLETE", "CANCELED"
    assert straddle._check_sell_without_buy(one, two) is True
    one.status, two.status = "OPEN", "CANCELLED"
    assert straddle._check_sell_without_buy(one, two) is True
    one.status, two.status = "OPEN", "TRIGGER PENDING"
    assert straddle._check_sell_without_buy(one, two) is False


def test_check_buy_without_sell(simple_straddle):
    straddle = simple_straddle
    straddle.create_order()
    one = straddle.order.orders[1]
    two = straddle.order.orders[3]
    assert straddle._check_buy_without_sell(one, two) is False
    one.status = "COMPLETE"
    assert straddle._check_buy_without_sell(one, two) is False
    one.status = two.status = "PENDING"
    assert straddle._check_buy_without_sell(one, two) is False
    one.status, two.status = "REJECTED", "COMPLETE"
    assert straddle._check_buy_without_sell(one, two) is True

    one.status, two.status = "COMPLETE", "CANCELED"
    assert straddle._check_buy_without_sell(one, two) is False
    one.status, two.status = "OPEN", "CANCELLED"
    assert straddle._check_buy_without_sell(one, two) is False

    one.status, two.status = "CANCELED", "PENDING"
    assert straddle._check_buy_without_sell(one, two) is True
    one.status, two.status = "TRIGGER PENDING", "OPEN"
    assert straddle._check_buy_without_sell(one, two) is False


def test_short_straddle_update_ltp(simple_straddle):
    straddle = simple_straddle
    straddle.update_ltp({"nifty": 4500})
    assert straddle.ltp == {"nifty22may17500ce": 0, "nifty22may17500pe": 0}
    straddle.update_ltp({"nifty22may17500ce": 120})
    assert straddle.ltp == {"nifty22may17500ce": 120, "nifty22may17500pe": 0}
    straddle.update_ltp({"nifty22may17500pe": 150})
    assert straddle.ltp == {"nifty22may17500ce": 120, "nifty22may17500pe": 150}
    straddle.update_ltp(
        {"a": 25, "b": 75, "nifty22may17500pe": 130, "nifty22may17500ce": 115}
    )
    assert straddle.ltp == {"nifty22may17500ce": 115, "nifty22may17500pe": 130}


def test_short_straddle_update_orders(price_straddle):
    straddle = price_straddle
    straddle.create_order()
    for o, i in zip(straddle.order.orders, range(10000, 10005)):
        o.id = i
    straddle.update_orders(
        {10000: {"filled_quantity": 50}, 10003: {"status": "COMPLETE"}}
    )
    assert straddle.order.orders[0].filled_quantity == 50
    assert straddle.order.orders[-1].status == "COMPLETE"


def test_short_straddle_make_sequential_orders_not_before_and_after_time(
    price_straddle,
):
    straddle = price_straddle
    known = pendulum.datetime(2022, 1, 1, 10, 5, tz="local")
    with pendulum.test(known):
        straddle.create_order()
        assert len(straddle.order.orders) == 4
        straddle._make_sequential_orders()
        assert len(straddle._pegs) == 2
    known = pendulum.datetime(2022, 2, 1, 10, 5, tz="local")
    with pendulum.test(known):
        straddle.create_order()
        assert len(straddle.order.orders) == 4
        straddle._make_sequential_orders()
        assert straddle._pegs[0].has_expired is True


def test_short_straddle_make_sequential_orders(price_straddle):
    known = pendulum.datetime(2022, 1, 1, 10, 11)
    with pendulum.test(known):
        straddle = price_straddle
        straddle._make_sequential_orders()
        assert len(straddle._pegs) == 0
        straddle.create_order()
        straddle._make_sequential_orders()
        assert len(straddle._pegs) == 2
        assert straddle._pegs[0].orders[0] == straddle.order.orders[0]
        assert straddle._pegs[1].orders[1] == straddle.order.orders[3]
