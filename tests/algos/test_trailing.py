from omspy.algos.trailing import *
import omspy.algos.trailing as tl
import pytest
import pendulum
from omspy.order import CompoundOrder, Order
from unittest.mock import patch


@pytest.fixture
def simple():
    known = pendulum.datetime(2025, 1, 1, tz="local")
    with pendulum.travel_to(known):
        return Trailing(
            start_time=known.add(hours=9),
            end_time=known.now().add(hours=15),
            start_trailing_at=1000,
            trailing_stop=500,
            trailing_step=300,
        )


@pytest.fixture
def simple_with_orders(simple):
    s = simple
    s.trailing_mtm = 400
    s.target = 2500
    order1 = Order(
        symbol="AAPL", side="BUY", quantity=750, filled_quantity=100, average_price=750
    )
    order2 = Order(
        symbol="MSFT", side="BUY", quantity=200, filled_quantity=200, average_price=400
    )
    s.add(order1)
    s.add(order2)
    s.ltps = dict(AAPL=750, MSFT=400)
    s.order.ltp.update(s.ltps)
    return s


def test_defaults(simple):
    s = simple
    assert s.start_time == pendulum.datetime(2025, 1, 1, 9, tz="local")
    assert s.end_time == pendulum.datetime(2025, 1, 1, 15, tz="local")
    assert s.start_trailing_at == 1000
    assert s.trailing_stop == 500
    assert s.trailing_step == 300
    assert isinstance(s.order, CompoundOrder)
    assert s.done is False


def test_trailing_with_order():
    co = CompoundOrder()
    order1 = Order(symbol="AAPL", side="BUY", quantity=100)
    co.add(order1)
    order2 = Order(symbol="AAPL", side="SELL", quantity=100)
    co.add(order2)
    trailing = Trailing(
        start_time=pendulum.now(), end_time=pendulum.now().add(hours=15), order=co
    )
    assert trailing.order == co
    assert id(co.orders[0]) == id(order1) == id(trailing.order.orders[0])
    assert id(co.orders[1]) == id(order2) == id(trailing.order.orders[1])


def test_get_trailing_stop_by_percent():
    assert tl._get_trailing_stop_by_percent(1000, 50) == 500
    assert tl._get_trailing_stop_by_percent(1000, 0.5) == 995
    assert tl._get_trailing_stop_by_percent(1000, 30) == 700


def test_get_trailing_stop_by_percent_trailing_step():
    assert tl._get_trailing_stop_by_percent(1174, 50, 100) == 550
    assert tl._get_trailing_stop_by_percent(1174, 50, 30) == 585
    assert tl._get_trailing_stop_by_percent(412, 50, 500) == 500


def test_get_trailing_stop_by_percent_negative():
    assert tl._get_trailing_stop_by_percent(-1000, 50) == -500
    assert round(tl._get_trailing_stop_by_percent(-1364, 19), 2) == -1104.84
    assert tl._get_trailing_stop_by_percent(-1034, 50, 300) == -450


def test_get_trailing_stop_by_percent_symmetry():
    assert tl._get_trailing_stop_by_percent(
        1000, 50
    ) == -tl._get_trailing_stop_by_percent(-1000, 50)
    assert tl._get_trailing_stop_by_percent(
        1150, 50, 300
    ) == -tl._get_trailing_stop_by_percent(-1150, 50, 300)


def test_get_trailing_stop_by_mtm():
    assert tl._get_trailing_stop_by_mtm(1250, 300) == 950
    assert tl._get_trailing_stop_by_mtm(1312, 117) == 1312 - 117


def test_get_trailing_stop_by_mtm_trailing_step():
    assert tl._get_trailing_stop_by_mtm(1154, 100) == 1054
    assert tl._get_trailing_stop_by_mtm(1154, 100, 100) == 1000
    assert tl._get_trailing_stop_by_mtm(1154, 100, 300) == 800
    assert tl._get_trailing_stop_by_mtm(1154, 250, 300) == 650
    assert tl._get_trailing_stop_by_mtm(380, 100, 500) == 500
    for a, b in zip(
        (214, 314, 514, 628, 1324, 1500, 1800), (600, 600, 600, 600, 1100, 1100, 1700)
    ):
        assert tl._get_trailing_stop_by_mtm(a, 100, 600) == b


def test_get_trailing_stop_by_mtm_negative():
    assert tl._get_trailing_stop_by_mtm(-1250, 300) == -950
    assert tl._get_trailing_stop_by_mtm(-1312, 117) == -1195
    assert tl._get_trailing_stop_by_mtm(-1273, 100, 200) == -1100
    assert tl._get_trailing_stop_by_mtm(-3274, 380, 500) == -2620
    assert tl._get_trailing_stop_by_mtm(-3274, 500, 380) == -2540


def test_get_trailing_stop_by_mtm_symmetry():
    assert tl._get_trailing_stop_by_mtm(1000, 50) == -tl._get_trailing_stop_by_mtm(
        -1000, 50
    )
    assert tl._get_trailing_stop_by_mtm(
        1150, 220, 300
    ) == -tl._get_trailing_stop_by_mtm(-1150, 220, 300)
    assert tl._get_trailing_stop_by_mtm(
        1150, 300, 220
    ) == -tl._get_trailing_stop_by_mtm(-1150, 300, 220)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ((1400,), (None, None)),
        ((-300, 600, 200), (200, 600)),
        ((1200, 1300), (None, 1300)),
        ((1178, 1150), (None, 1150)),
        ((130, None, 140), (140, None)),
        ((129, 150, 110), (110, 150)),
        ((1300, None, None, 50), (650, None)),
        ((1300, 2200, None, 50), (650, 2200)),
        ((1300, None, -1000, 50), (650, None)),
        ((-1300, 2200, -1000, 50), (-650, 2200)),
        ((-1300, 2200, -1000, 10), (-1170, 2200)),
        ((1674, 2400, -1500, 50, None, 300), (750, 2400)),
        ((1674, 2400, -1500, 50, 550, 300), (750, 2400)),
        ((1850, 1600), (None, 1600)),
        ((-1200, 1600, -700), (-700, 1600)),
        ((2178, 2600, -1500, 50, None, None, 1800), (1089, 2600)),
        ((1178, 2600, -1500, 50, None, None, 1800), (-1500, 2600)),
        ((1578, 2600, -1500, 50, 300, 600, 1100), (600, 2600)),
        ((1240, 1200, None), (None, 1200)),
        ((1240, None, -1000), (-1000, None)),
        ((1240, 1200, -1000), (-1000, 1200)),
        ((1200, 1200, -1000, None, 300, None, None), (900, 1200)),
        ((-300, 1200, -1000, None, 600, None, None), (300, 1200)),
        ((-1200, 1200, -1000, None, 600, None, None), (-600, 1200)),
        ((1300, 1200, -1000, None, 300, 300, None), (900, 1200)),
        ((1300, 1200, -1000, None, 300, 300, 1500), (-1000, 1200)),
        ((1300, 1200, -1000, None, 300, 300, 1000), (900, 1200)),
        ((1100, 1200, -1000, None, 300, 300, 1000), (600, 1200)),
    ],
    ids=[
        "no_tgt_no_stop",
        "mtm_lt_stop",
        "tgt_no_stop",
        "tgt_no_stop2",
        "no_tgt_stop",
        "tgt_stop",
        "per_no_tgt_no_stop",
        "per_tgt_no_stop",
        "per_no_tgt_stop",
        "per_tgt_stop",
        "per_tgt_stop2",
        "per_tgt_stop_trl_step",
        "per_dis_mtm",
        "mtm_gt_tgt",
        "mtm_lt_stop",
        "per_trl_start_at",
        "per_trl_start_at2",
        "per_trl_start_at_step",
        "mtm_tgt_no_stop",
        "mtm_no_tgt_stop",
        "mtm_tgt_stop",
        "mtm_trl",
        "mtm_trl_neg",
        "mtm_trl_neg2",
        "mtm_trl_step",
        "mtm_trl_step_at",
        "mtm_trl_step_at2",
        "mtm_trl_step_at3",
    ],
)
def test_get_trailing_stop_and_target(test_input, expected):
    assert get_trailing_stop_and_target(*test_input) == trailing_values(
        stop=expected[0], target=expected[1]
    )


def test_can_start_trail_time(simple):
    s = simple
    s.start_trailing_at = None
    known = pendulum.datetime(2025, 1, 1, tz="local")
    with pendulum.travel_to(known):
        pendulum.travel(hours=8, minutes=59)
        assert s.can_trail is False
        pendulum.travel(minutes=1)
        assert s.can_trail is True
        pendulum.travel(hours=3)
        assert s.can_trail is True
        pendulum.travel(hours=3, minutes=21)
        assert s.can_trail is False
        # Change time
        s.end_time = pendulum.datetime(2025, 1, 1, 16, tz="local")
        assert s.can_trail is True


def test_can_start_trail_start_trailing_at(simple):
    s = simple
    assert s.mtm == 0
    assert s.order.count == 0
    known = pendulum.datetime(2025, 1, 1, 9, 15, tz="local")
    with pendulum.travel_to(known):
        assert s.can_trail is False
        values = (900, 1000, 1100, 950)
        expected = (False, True, True, True)
        # Once mtm is greater than start_trailing_at, trailing must start even if it comes down afterwards
        for v, e in zip(values, expected):
            with patch("omspy.algos.trailing.Trailing.mtm", v):
                assert s.can_trail is e


def test_trailing_add(simple):
    s = simple
    assert s.order.count == 0
    s.add(Order(symbol="AAPL", side="BUY", quantity=100))
    assert s.order.count == 1


def test_trailing_done(simple):
    s = simple
    assert s.done is False
    s.add(
        Order(
            symbol="AAPL",
            side="BUY",
            quantity=100,
            filled_quantity=100,
            average_price=100,
        )
    )
    s.run({"AAPL": 100})
    assert s.done is False
    s.target = 2000
    values = (94.8, 102, 107, 128)
    expected = (True, False, False, True)
    for v, e in zip(values, expected):
        s.run({"AAPL": v})
        assert s.done is e
    # set stop and target to none and check
    s.trailing_stop = None
    s.target = None
    s.run({"AAPL": 1e50})
    assert s.done is False
    s.run({"AAPL": 0})
    assert s.done is False


def test_trailing_update(simple_with_orders):
    s = simple_with_orders
    assert s.mtm == 0
    known = pendulum.datetime(2025, 1, 1, tz="local")
    with pendulum.travel_to(known.add(hours=10)):
        result = s.update(dict())
        expected = TrailingResult(
            done=False,
            stop=500,
            target=2500,
            next_trail_at=None,
        )
        assert result == expected
        result = s.update({"AAPL": 770})
        expected = TrailingResult(
            done=False,
            stop=1400,
            target=2500,
            next_trail_at=2100,
        )
        assert result == expected
        assert s.trailing_stop == 1400
        assert s.next_trail == 2100
        assert s.done is False
        # Do not update trailing stop if price goes down
        result = s.update({"AAPL": 760})
        assert result == expected
        assert s.done is False
        # test target
        result = s.update({"MSFT": 490})
        expected = TrailingResult(
            done=True, stop=18500, target=2500, next_trail_at=19200
        )
        assert s.done is True
        assert s.trailing_stop == 18500
        assert result == expected
