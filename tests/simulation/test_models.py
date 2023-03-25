from omspy.simulation.models import *
from omspy.simulation.virtual import generate_orderbook
import pendulum
import pytest
import random


@pytest.fixture
def basic_ticker():
    return Ticker(name="aapl", token=1234, initial_price=125)


@pytest.fixture
def vtrade():
    return VTrade(
        trade_id="202310001",
        order_id="20234567812",
        symbol="aapl",
        quantity=50,
        price=120,
        side=Side.BUY,
        timestamp=pendulum.datetime(2023, 1, 2, 7, 10),
    )


@pytest.fixture
def vorder_kwargs():
    return dict(
        order_id="20234567812",
        symbol="aapl",
        quantity=100,
        side=1,
        exchange_timestamp=pendulum.datetime(2023, 1, 2, 7, 10),
    )


@pytest.fixture
def vorder_simple(vorder_kwargs):
    return VOrder(**vorder_kwargs)


@pytest.fixture
def ohlc_args():
    return dict(open=104, high=112, low=101, close=108, last_price=107)


def test_vtrade_defaults(vtrade):
    assert vtrade.price == 120
    assert vtrade.side == Side.BUY
    assert vtrade.value == 6000


def test_vorder_defaults(vorder_kwargs):
    vorder = VOrder(**vorder_kwargs)
    assert vorder.quantity == 100
    assert vorder.side == Side.BUY
    assert vorder.status_message is None
    assert vorder.timestamp is not None
    assert vorder.filled_quantity == 0
    assert vorder.pending_quantity == 100
    assert vorder.canceled_quantity == 0
    assert vorder.average_price == 0


def test_vorder_quantities(vorder_kwargs):
    vorder_kwargs["pending_quantity"] = 50
    vorder = VOrder(**vorder_kwargs)
    assert vorder.quantity == 100
    assert vorder.filled_quantity == 50
    assert vorder.pending_quantity == 50
    assert vorder.canceled_quantity == 0

    vorder_kwargs["filled_quantity"] = 100
    vorder = VOrder(**vorder_kwargs)
    assert vorder.quantity == 100
    assert vorder.filled_quantity == 100
    assert vorder.pending_quantity == 0
    assert vorder.canceled_quantity == 0

    vorder_kwargs["canceled_quantity"] = 100
    vorder = VOrder(**vorder_kwargs)
    assert vorder.quantity == 100
    assert vorder.filled_quantity == 0
    assert vorder.pending_quantity == 0
    assert vorder.canceled_quantity == 100


def test_vposition_defaults():
    pos = VPosition(symbol="aapl")
    assert pos.buy_quantity is None
    assert pos.sell_quantity is None
    assert pos.buy_value is None
    assert pos.sell_value is None
    assert pos.average_buy_price == 0
    assert pos.average_sell_price == 0
    assert pos.net_quantity == 0
    assert pos.net_value == 0


def test_vorder_status(vorder_kwargs):
    order = VOrder(**vorder_kwargs)
    assert order.filled_quantity == 0
    assert order.pending_quantity == 100
    assert order.status == Status.OPEN

    order.filled_quantity = 100
    assert order.status == Status.COMPLETE

    order.filled_quantity = 40
    order.canceled_quantity = 60
    order.pending_quantity = 0
    assert order.status == Status.PARTIAL_FILL

    order.filled_quantity = 40
    order.pending_quantity = 60
    order.canceled_quantity = 0
    assert order.status == Status.PENDING


def test_vorder_status_canceled_rejected(vorder_kwargs):
    order = VOrder(**vorder_kwargs)
    assert order.filled_quantity == 0
    assert order.pending_quantity == 100
    assert order.status == Status.OPEN

    order.filled_quantity = order.pending_quantity = 0
    order.canceled_quantity = 100
    assert order.status == Status.CANCELED

    order.status_message = "REJECTED: no margins"
    assert order.status == Status.REJECTED

    # test with lower case
    order.status_message = "rejected: no margins"
    assert order.status == Status.REJECTED


def test_vtrade_value(vtrade):
    assert vtrade.value == 6000
    vtrade.side = Side.SELL
    vtrade.price = 100
    assert vtrade.value == -5000


def test_vorder_value(vorder_kwargs):
    order = VOrder(**vorder_kwargs)
    order.average_price = 120
    assert order.value == 0
    order.filled_quantity = 50
    assert order.value == 6000
    order.filled_quantity = 100
    assert order.value == 12000
    order.side = -1
    assert order.value == -12000
    assert order.side == Side.SELL


def test_vorder_value_price(vorder_kwargs):
    order = VOrder(**vorder_kwargs)
    assert order.value == 0
    order.filled_quantity = 50
    order.price = 118
    assert order.value == 5900
    order.average_price = 120
    assert order.value == 6000


def test_vposition_price():
    pos = VPosition(
        symbol="aapl",
        buy_quantity=100,
        buy_value=10000,
        sell_quantity=50,
        sell_value=5100,
    )
    assert pos.average_buy_price == 100
    assert pos.average_sell_price == 5100 / 50
    assert pos.net_quantity == 50
    assert pos.net_value == 4900

    pos.sell_quantity = 120
    pos.sell_value = 12240
    assert pos.average_sell_price == 102
    assert pos.net_value == -2240


def test_response():
    known = pendulum.datetime(2023, 2, 1, 12, 44, tz="local")
    with pendulum.test(known):
        resp = Response(status="success")
        assert resp.status == ResponseStatus.SUCCESS
        assert resp.timestamp == known


def test_order_response():
    data = VOrder(order_id="order_id", symbol="aapl", quantity=10, side=1, price=100)
    order_response = OrderResponse(status="success", data=data)
    d = order_response.data
    assert order_response.status == "success"
    assert d.order_id == "order_id"
    assert d.symbol == "aapl"
    assert d.quantity == 10
    assert d.side == Side.BUY
    assert d.price == 100
    assert d.trigger_price is None
    assert d.filled_quantity == 0
    assert d.canceled_quantity == 0
    assert d.pending_quantity == 10
    assert d.status == Status.OPEN


def test_ohlc(ohlc_args):
    ohlc = OHLC(**ohlc_args)
    assert ohlc.open == 104
    assert ohlc.high == 112
    assert ohlc.low == 101
    assert ohlc.close == 108
    assert ohlc.last_price == 107


def test_ohlcv(ohlc_args):
    ohlc_args["volume"] = 12600
    ohlc = OHLCV(**ohlc_args)
    assert ohlc.open == 104
    assert ohlc.high == 112
    assert ohlc.low == 101
    assert ohlc.close == 108
    assert ohlc.last_price == 107
    assert ohlc.volume == 12600


def test_ohlcvi(ohlc_args):
    ohlc_args["volume"] = 12600
    ohlc_args["open_interest"] = 13486720
    ohlc = OHLCVI(**ohlc_args)
    assert ohlc.open == 104
    assert ohlc.high == 112
    assert ohlc.low == 101
    assert ohlc.close == 108
    assert ohlc.last_price == 107
    assert ohlc.volume == 12600
    assert ohlc.open_interest == 13486720


def test_vquote(ohlc_args):
    ohlc_args["volume"] = 22000
    orderbook = generate_orderbook()
    quote = VQuote(orderbook=orderbook, **ohlc_args)
    assert quote.open == 104
    assert quote.high == 112
    assert quote.low == 101
    assert quote.close == 108
    assert quote.last_price == 107
    assert quote.volume == 22000
    assert len(quote.orderbook.ask) == 5
    assert len(quote.orderbook.bid) == 5


def test_generic_response(ohlc_args):
    data = VOrder(order_id="order_id", symbol="aapl", quantity=10, side=1, price=100)
    response = GenericResponse(status="success", data=data)
    assert response.data.price == 100

    data = OHLC(**ohlc_args)
    response = GenericResponse(status="success", data=data)
    assert response.data.high == 112
    assert response.data.last_price == 107


def test_vuser_defaults():
    user = VUser(userid="ABCD1234")
    assert user.userid == "ABCD1234"
    assert user.name is None
    assert user.orders == []


def test_vuser_add(vorder_kwargs):
    user = VUser(userid="abcd1234")
    assert user.userid == "ABCD1234"
    order = VOrder(**vorder_kwargs)
    user.add(order)
    assert user.orders[0] == order
    assert len(user.orders) == 1


@pytest.mark.parametrize(
    "filled,pending,canceled,expected",
    [
        (0, 100, 0, False),
        (50, 100, 0, False),
        (100, 0, 0, True),
        (50, 50, 0, False),
        (50, 0, 50, True),
        (50, 0, 100, True),
    ],
)
def test_vorder_is_done(vorder_kwargs, filled, pending, canceled, expected):
    order = VOrder(
        filled_quantity=filled,
        pending_quantity=pending,
        canceled_quantity=canceled,
        **vorder_kwargs
    )
    assert order.is_done is expected
    pass


def test_vorder_is_past_delay(vorder_kwargs):
    known = pendulum.datetime(2023, 1, 1, 11, 20, tz="local")
    with pendulum.test(known):
        order = VOrder(**vorder_kwargs)
        assert order.is_past_delay is False
    with pendulum.test(known.add(seconds=3)):
        assert order.is_past_delay is True


def test_vorder_custom_delay(vorder_kwargs):
    known = pendulum.datetime(2023, 1, 1, 11, 20, tz="local")
    with pendulum.test(known):
        order = VOrder(**vorder_kwargs)
        order._delay = 5e6
        assert order.is_past_delay is False
    with pendulum.test(known.add(seconds=3)):
        assert order.is_past_delay is False
    with pendulum.test(known.add(seconds=5)):
        assert order.is_past_delay is False


def test_vorder_modify_by_status_complete(vorder_simple):
    order = vorder_simple
    order._modify_order_by_status(Status.COMPLETE)
    assert order.quantity == order.filled_quantity
    assert order.pending_quantity == order.canceled_quantity == 0
    assert order.status == Status.COMPLETE
    assert order.is_done is True


def test_vorder_modify_by_status_canceled(vorder_simple):
    order = vorder_simple
    order._modify_order_by_status(Status.CANCELED)
    assert order.quantity == order.canceled_quantity
    assert order.pending_quantity == order.filled_quantity == 0
    assert order.status == Status.CANCELED
    assert order.is_done is True


def test_vorder_modify_by_status_open(vorder_simple):
    order = vorder_simple
    order._modify_order_by_status(Status.OPEN)
    assert order.quantity == order.pending_quantity
    assert order.canceled_quantity == order.filled_quantity == 0
    assert order.status == Status.OPEN
    assert order.is_done is False


def test_vorder_modify_by_status_partial_fill(vorder_simple):
    order = vorder_simple
    order._modify_order_by_status(Status.PARTIAL_FILL)
    assert order.filled_quantity > 0
    assert order.canceled_quantity > 0
    assert order.pending_quantity == 0
    assert (
        order.filled_quantity + order.canceled_quantity + order.pending_quantity
        == order.quantity
    )
    assert order.status == Status.PARTIAL_FILL
    assert order.is_done is True


def test_vorder_modify_by_status_pending(vorder_simple):
    order = vorder_simple
    order._modify_order_by_status(Status.PENDING)
    assert order.filled_quantity > 0
    assert order.pending_quantity > 0
    assert order.canceled_quantity == 0
    assert (
        order.filled_quantity + order.canceled_quantity + order.pending_quantity
        == order.quantity
    )
    assert order.status == Status.PENDING
    assert order.is_done is False


def test_vorder_modify_by_status(vorder_kwargs):
    known = pendulum.datetime(2023, 1, 1, 11, 20, tz="local")
    with pendulum.test(known):
        order = VOrder(**vorder_kwargs)
        order.modify_by_status()
        assert order.is_done is False
        assert order.filled_quantity == 0
    with pendulum.test(known.add(seconds=1)):
        order.modify_by_status()
        assert order.status == Status.OPEN
    with pendulum.test(known.add(seconds=2)):
        order.modify_by_status()
        assert order.status == Status.COMPLETE
        assert order.is_done is True
        assert order.filled_quantity == 100


def test_vorder_modify_by_status_do_not_modify_done(vorder_kwargs):
    known = pendulum.datetime(2023, 1, 1, 11, 20, tz="local")
    with pendulum.test(known):
        order = VOrder(**vorder_kwargs)
    with pendulum.test(known.add(seconds=2)):
        order.modify_by_status()
        assert order.status == Status.COMPLETE
    with pendulum.test(known.add(seconds=5)):
        order.modify_by_status(Status.CANCELED)
        assert order.status == Status.COMPLETE


def test_vorder_modify_by_status_partial_fill(vorder_kwargs):
    known = pendulum.datetime(2023, 1, 1, 11, 20, tz="local")
    with pendulum.test(known):
        order = VOrder(**vorder_kwargs)
    with pendulum.test(known.add(seconds=2)):
        order.modify_by_status(Status.PARTIAL_FILL)
        assert order.filled_quantity < order.quantity
        assert order.canceled_quantity > 0
        assert order.pending_quantity == 0
        assert order.is_done is True


def test_ticker_defaults():
    ticker = Ticker(name="abcd")
    assert ticker.name == "abcd"
    assert ticker.token is None
    assert ticker.initial_price == 100
    assert ticker.mode == TickerMode.RANDOM
    assert ticker._high == ticker._low == ticker._ltp == 100


def test_ticker_is_random():
    ticker = Ticker(name="abcd")
    assert ticker.is_random is True
    ticker.mode = TickerMode.MANUAL
    assert ticker.is_random is False


def test_ticker_ltp(basic_ticker):
    random.seed(1000)
    ticker = basic_ticker
    for i in range(15):
        ticker.ltp
    assert ticker._ltp == 120.5
    assert ticker._high == 125.3
    assert ticker._low == 120.5


def test_ticker_ohlc(basic_ticker):
    ticker = basic_ticker
    ticker.ohlc() == dict(open=125, high=125, low=125, close=125)
    for i in range(15):
        ticker.ltp
    ticker.ohlc() == dict(open=125, high=125, low=116.95, close=120)


def test_ticker_ticker_mode(basic_ticker):
    ticker = basic_ticker
    ticker.mode = TickerMode.MANUAL
    for i in range(3):
        print(ticker.ltp)
    assert ticker.ltp == 125
    ticker.mode = TickerMode.RANDOM
    assert ticker.ltp != 125


def test_ticker_update(basic_ticker):
    ticker = basic_ticker
    for ltp in (128, 123, 124, 126):
        ticker.update(ltp)
    assert ticker.ohlc() == dict(open=125, high=128, low=123, close=126)
