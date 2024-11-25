from omspy.simulation.virtual import *
import pytest
import pendulum
import random
from unittest.mock import patch, Mock
from pydantic import ValidationError
from dataclasses import dataclass, asdict
import string


def generate_instrument(**kwargs):
    """
    generate a random instrument
    """
    inst_args = dict()
    name = "".join(random.choices(string.ascii_uppercase, k=random.randrange(4, 11)))
    if "name" in kwargs:
        name = kwargs.get("name")
        kwargs.pop("name")
    inst_args["name"] = name
    if "last_price" in kwargs:
        return Instrument(name=name, **kwargs)
    else:
        last_price = random.randrange(100, 200)
        open_price = last_price + random.randrange(1, 10)
        high = open_price + random.randrange(2, 20)
        low = open_price - random.randrange(2, 20)
        close = (last_price + open_price) / 2
        inst_args.update(
            dict(
                last_price=last_price, open=open_price, high=high, low=low, close=close
            )
        )
        inst_args.update(kwargs)
        return Instrument(**inst_args)


@pytest.fixture
def basic_broker() -> VirtualBroker:
    tickers = dict(
        aapl=Ticker(name="aapl", token=1111, initial_price=100),
        goog=Ticker(name="goog", token=2222, initial_price=125),
        amzn=Ticker(name="amzn", token=3333, initial_price=260),
    )
    return VirtualBroker(tickers=tickers)


@pytest.fixture
def basic_broker_with_users(basic_broker) -> VirtualBroker:
    basic_broker.add_user(VUser(userid="abcd1234"))
    basic_broker.add_user(VUser(userid="xyz456"))
    basic_broker.add_user(VUser(userid="bond007"))
    return basic_broker


@pytest.fixture
def basic_broker_with_prices(basic_broker) -> VirtualBroker:
    prices = [
        dict(aapl=105, goog=121, amzn=264),
        dict(aapl=102, goog=124, amzn=258),
        dict(aapl=99, goog=120, amzn=260),
        dict(aapl=106, goog=122, amzn=259),
        dict(aapl=103, goog=123, amzn=261),
    ]
    for last_price in prices:
        basic_broker.update_tickers(last_price)
    return basic_broker


@pytest.fixture
def replica_with_instruments() -> ReplicaBroker:
    random.seed(1000)
    broker = ReplicaBroker()
    names = ["AAPL", "XOM", "DOW"]
    instruments = []
    for name in names:
        inst = generate_instrument(name=name)
        instruments.append(inst)
    broker.update(instruments)
    return broker


@pytest.fixture
def replica_with_orders(replica_with_instruments) -> ReplicaBroker:
    @dataclass
    class Inputs:
        symbol: str
        side: int  # replace with enum by order
        quantity: int
        order_type: int  # replaced with enum by order
        price: float
        user: str

    order_inputs = [
        Inputs("AAPL", 1, 10, 1, 124, "user1"),
        Inputs("AAPL", -1, 10, 2, 126, "default"),
        Inputs("AAPL", 1, 20, 2, 124, "user2"),
        Inputs("DOW", -1, 13, 1, 124, "user1"),
        Inputs("DOW", 1, 18, 1, 124, "user2"),
        Inputs("XOM", 1, 20, 2, 154, "user2"),  # passed
        Inputs("XOM", 1, 30, 2, 135, "default"),
        Inputs("XOM", -1, 30, 2, 140, "default"),  # passed
        Inputs("AAPL", 1, 10, 2, 123, "default"),
        Inputs("AAPL", 1, 10, 2, 122, "default"),
    ]
    broker = replica_with_instruments
    for inputs in order_inputs:
        broker.order_place(**asdict(inputs))
    return broker


def test_generate_price():
    random.seed(100)
    assert generate_price() == 102
    assert generate_price(1000, 2000) == 1470
    assert generate_price(110, 100) == 107


def test_generate_price_same_start_and_end():
    with patch("random.randrange") as randrange:
        price = generate_price(100, 100)
        randrange.assert_called_once_with(100, 110)
    with patch("random.randrange") as randrange:
        price = generate_price(1000, 1000)
        randrange.assert_called_once_with(1000, 1100)
    with patch("random.randrange") as randrange:
        price = generate_price(4, 4)
        randrange.assert_called_once_with(4, 6)


def test_generate_orderbook_default():
    ob = generate_orderbook()
    ob.bid[-1].price == 99.96
    ob.ask[-1].price == 100.04
    for b in ob.bid:
        assert 50 < b.quantity < 150
    for a in ob.ask:
        assert 50 < b.quantity < 150


def test_generate_orderbook_swap_bid_ask():
    ob = generate_orderbook(bid=100.05, ask=100)
    ob.bid[-1].price == 99.96
    ob.ask[-1].price == 100.04
    for b in ob.bid:
        assert 50 <= b.quantity <= 150
    for a in ob.ask:
        assert 50 <= b.quantity <= 150


def test_generate_orderbook_depth():
    ob = generate_orderbook(depth=100)
    ob.bid[-1].price == 99.01
    ob.ask[-1].price == 100.99
    assert len(ob.bid) == 100
    assert len(ob.ask) == 100


def test_generate_orderbook_price_and_tick_and_quantity():
    ob = generate_orderbook(bid=1000, ask=1005, tick=2, depth=10, quantity=600)
    ob.bid[-1].price == 982
    ob.ask[-1].price == 1023
    assert len(ob.bid) == len(ob.ask) == 10
    for b in ob.bid:
        assert 300 <= b.quantity <= 900
    for a in ob.ask:
        assert 300 <= b.quantity <= 900


def test_generate_orderbook_orders_count():
    with patch("random.randrange") as randrange:
        randrange.side_effect = [10, 10, 100, 100] * 20
        ob = generate_orderbook()
    for a, b in zip(ob.ask, ob.bid):
        assert a.orders_count <= a.quantity
        assert b.orders_count <= b.quantity


def test_virtual_broker_defaults(basic_broker):
    b = basic_broker
    assert b.name == "VBroker"
    assert len(b.tickers) == 3
    assert b.failure_rate == 0.001


def test_virtual_broker_is_failure(basic_broker):
    b = basic_broker
    assert b.is_failure is False
    b.failure_rate = 1.0  # everything should fail now
    assert b.is_failure is True
    with pytest.raises(ValidationError):
        b.failure_rate = -1
    with pytest.raises(ValidationError):
        b.failure_rate = 2


def test_virtual_broker_order_place_success(basic_broker):
    b = basic_broker
    known = pendulum.datetime(2023, 2, 1, 10, 17)
    with pendulum.travel_to(known, freeze=True):
        response = b.order_place(symbol="aapl", quantity=10, side=1)
        assert response.status == "success"
        assert response.timestamp == known
        assert response.data.order_id is not None
    assert len(b._orders) == 1


def test_virtual_broker_order_place_success_fields(basic_broker):
    b = basic_broker
    known = pendulum.datetime(2023, 2, 1, 10, 17)
    with pendulum.travel_to(known, freeze=True):
        response = b.order_place(
            symbol="aapl", quantity=10, side=1, price=100, trigger_price=99
        )
        d = response.data
        assert response.status == "success"
        assert response.timestamp == known
        assert response.data.order_id is not None
        assert d.price == 100
        assert d.trigger_price == 99
        assert d.symbol == "aapl"
        assert d.quantity == 10
        assert d.side == Side.BUY
        assert d.filled_quantity == 0
        assert d.canceled_quantity == 0
        assert d.pending_quantity == 10
        assert d.status == Status.OPEN


def test_virtual_broker_order_place_failure(basic_broker):
    b = basic_broker
    b.failure_rate = 1.0
    known = pendulum.datetime(2023, 2, 1, 10, 17)
    with pendulum.travel_to(known):
        response = b.order_place(symbol="aapl", quantity=10, side=1, price=100)
        assert response.status == "failure"
        assert response.timestamp == known
        assert response.data is None


def test_virtual_broker_order_place_user_response(basic_broker):
    b = basic_broker
    b.failure_rate = 1.0
    response = b.order_place(response=dict(symbol="aapl", price=100))
    assert response == {"symbol": "aapl", "price": 100}


def test_virtual_broker_order_place_validation_error(basic_broker):
    b = basic_broker
    known = pendulum.datetime(2023, 2, 1, 10, 17)
    with pendulum.travel_to(known, freeze=True):
        response = b.order_place()
        assert response.status == "failure"
        assert response.timestamp == known
        assert response.error_msg.startswith("Found 3 validation")
        assert response.data is None

        response = b.order_place(symbol="aapl", side=-1)
        assert response.status == "failure"
        assert response.timestamp == known
        assert response.error_msg.startswith("Found 1 validation")
        assert "quantity" in response.error_msg
        assert response.data is None


def test_virtual_broker_get(basic_broker):
    b = basic_broker
    for i in (50, 100, 130):
        b.order_place(symbol="dow", side=1, quantity=i)
    assert len(b._orders) == 3
    order_id = list(b._orders.keys())[1]
    assert b.get(order_id) == list(b._orders.values())[1]


def test_virtual_broker_order_modify(basic_broker):
    b = basic_broker
    order = b.order_place(symbol="dow", side=1, quantity=50)
    order_id = order.data.order_id
    resp = b.order_modify(order_id, quantity=25)
    assert resp.status == "success"
    assert resp.data.quantity == 25
    resp = b.order_modify(order_id, price=1000)
    assert resp.status == "success"
    assert resp.data.price == 1000
    assert list(b._orders.values())[0].price == 1000


def test_virtual_broker_order_modify_failure(basic_broker):
    b = basic_broker
    order = b.order_place(symbol="dow", side=1, quantity=50)
    order_id = order.data.order_id
    resp = b.order_modify("hexid", quantity=25)
    assert resp.status == "failure"
    assert resp.data is None
    b.failure_rate = 1.0
    resp = b.order_modify(order_id, price=100)
    assert resp.status == "failure"
    assert resp.data is None


def test_virtual_broker_order_modify_kwargs_response(basic_broker):
    b = basic_broker
    resp = b.order_modify("hexid", quantity=25, response=dict(a=10, b=15))
    assert resp == dict(a=10, b=15)


def test_virtual_broker_order_cancel(basic_broker):
    b = basic_broker
    order = b.order_place(symbol="dow", side=1, quantity=50)
    order_id = order.data.order_id
    resp = b.order_cancel(order_id)
    assert resp.status == "success"
    assert resp.data.canceled_quantity == 50
    assert resp.data.filled_quantity == 0
    assert resp.data.pending_quantity == 0
    assert resp.data.status == Status.CANCELED


def test_virtual_broker_order_cancel_failure(basic_broker):
    b = basic_broker
    order = b.order_place(symbol="dow", side=1, quantity=50)
    order_id = order.data.order_id
    resp = b.order_modify("hexid", quantity=25)
    assert resp.status == "failure"
    assert resp.data is None
    order = b.get(order_id)
    order.filled_quantity = 50
    assert resp.status == "failure"


def test_virtual_broker_order_cancel_kwargs_response(basic_broker):
    b = basic_broker
    resp = b.order_cancel("hexid", quantity=25, response=dict(a=10, b=15))
    assert resp == dict(a=10, b=15)


def test_fake_broker_ltp():
    b = FakeBroker()
    random.seed(1000)
    assert b.ltp("aapl") == {"aapl": 106}
    random.seed(1000)
    assert b.ltp("aapl", end=150) == {"aapl": 149}
    random.seed(1000)
    assert b.ltp("goog", start=1000, end=1200) == {"goog": 1199}


def test_fake_broker_orderbook():
    b = FakeBroker()
    ob = b.orderbook("aapl")
    assert "aapl" in ob
    obook = ob["aapl"]
    assert len(obook.ask) == 5
    assert len(obook.bid) == 5

    ob = b.orderbook("goog", bid=400, ask=405, depth=10, tick=1)
    obook = ob["goog"]
    assert obook.bid[-1].price == 391
    assert obook.ask[-1].price == 414
    assert obook.bid[0].price == 400
    assert obook.ask[0].price == 405
    assert len(obook.bid) == len(obook.ask) == 10
    assert len(obook.bid) == len(obook.ask) == 10


def test_generate_ohlc_default():
    random.seed(1001)
    ohlc = generate_ohlc()
    assert ohlc.open == 100
    assert ohlc.high == 103
    assert ohlc.low == 100
    assert ohlc.close == 102
    assert ohlc.last_price == 101
    assert ohlc.volume == 17876


def test_generate_ohlc_custom():
    random.seed(1002)
    ohlc = generate_ohlc(300, 380, 2e6)
    assert ohlc.open == 372
    assert ohlc.high == 376
    assert ohlc.low == 366
    assert ohlc.close == 369
    assert ohlc.last_price == 368
    assert ohlc.volume == 1546673


def test_fake_broker_ohlc():
    b = FakeBroker()
    random.seed(1001)
    quote = b.ohlc("goog")
    ohlc = quote["goog"]
    assert ohlc.open == 100
    assert ohlc.last_price == 101
    assert ohlc.volume == 17876

    random.seed(1001)
    quote = b.ohlc("aapl", start=400, end=450, volume=45000)
    ohlc = quote["aapl"]
    assert ohlc.high == 448
    assert ohlc.low == 403
    assert ohlc.last_price == 438
    assert ohlc.volume == 71954


def test_fake_broker_order_place():
    b = FakeBroker()
    random.seed(1000)
    order = b.order_place()
    assert order.symbol == "JPM"
    assert order.quantity == 1634
    assert order.side == Side.SELL
    assert order.price == 404
    assert order.filled_quantity == 1634
    assert order.pending_quantity == 0
    assert order.canceled_quantity == 0


def test_fake_broker_order_place_kwargs():
    b = FakeBroker()
    random.seed(1000)
    order = b.order_place(symbol="aapl", price=360, trigger_price=320, side=1)
    assert order.symbol == "aapl"
    assert order.quantity == 7038
    assert order.side == Side.BUY
    assert order.price == 360
    assert order.trigger_price == 320
    assert order.filled_quantity == 7038
    assert order.pending_quantity == 0
    assert order.canceled_quantity == 0


def test_fake_broker_quote():
    b = FakeBroker()
    random.seed(1200)
    quote = b.quote(symbol="goog")["goog"]
    assert quote.last_price == 104
    assert quote.high == 109
    assert quote.orderbook.ask[0].price == 106.01


def test_fake_broker_quote_kwargs_price():
    b = FakeBroker()
    random.seed(1200)
    quote = b.quote(symbol="goog", start=150, end=200)["goog"]
    assert quote.last_price == 171
    assert quote.high == 189
    assert quote.orderbook.ask[0].price == 177.01


def test_fake_broker_quote_kwargs_orderbook():
    b = FakeBroker()
    random.seed(1200)
    quote = b.quote(symbol="goog", start=150, end=200, volume=1e8, depth=15, tick=1)[
        "goog"
    ]
    assert quote.last_price == 171
    assert quote.high == 189
    assert quote.volume == 102924217
    assert len(quote.orderbook.ask) == len(quote.orderbook.bid) == 15
    assert quote.orderbook.ask[0].price == 178
    assert quote.orderbook.ask[-1].price == 192
    assert quote.orderbook.bid[0].price == 177
    assert quote.orderbook.bid[-1].price == 163


def test_fake_broker_ltps():
    b = FakeBroker()
    random.seed(1000)
    assert b.ltp(("aapl", "goog")) == dict(aapl=106, goog=101)
    random.seed(1000)
    assert b.ltp(list("abcd"), start=1000, end=1200) == dict(
        a=1199, b=1109, c=1171, d=1194
    )


def test_fake_broker_ltps_iterables():
    from collections import Counter

    lst = list("abcd")
    tup = tuple("abcd")
    dct = Counter("abcd")
    st = set("abcd")
    b = FakeBroker()
    random.seed(1000)
    assert b.ltp(lst, start=1000, end=1200) == dict(a=1199, b=1109, c=1171, d=1194)
    random.seed(1000)
    assert b.ltp(tup, start=1000, end=1200) == dict(a=1199, b=1109, c=1171, d=1194)
    random.seed(1000)
    assert b.ltp(dct, start=1000, end=1200) == dict(a=1199, b=1109, c=1171, d=1194)
    random.seed(1000)
    assert b.ltp(sorted(st), start=1000, end=1200) == dict(
        a=1199, b=1109, c=1171, d=1194
    )


def test_fake_broker_ltps_non_iterable():
    b = FakeBroker()
    random.seed(1000)
    assert b.ltp(100) == dict()


def test_fake_broker_orderbook_multi():
    b = FakeBroker()
    symbols = list("abcdef")
    orderbook = b.orderbook(symbols, depth=10, tick=2, ask=1000, bid=1003)
    assert len(orderbook) == 6
    assert list(orderbook.keys()) == list("abcdef")
    for k, v in orderbook.items():
        assert type(v) == OrderBook
        assert len(v.ask) == len(v.bid) == 10
        assert v.ask[-1].price == 1021
        assert v.bid[-1].price == 982


def test_fake_broker_ohlc_multi():
    b = FakeBroker()
    symbols = list("abcdef")
    ohlc = b.ohlc(symbols, start=50, end=400)
    for k, v in ohlc.items():
        assert v.high < 400
        assert v.low >= 50


def test_fake_broker_multi_quote():
    b = FakeBroker()
    symbols = list("abcdef")
    quotes = b.quote(symbols, start=100, end=500, depth=10)
    for k, v in quotes.items():
        assert 100 < v.last_price < 500
        assert len(v.orderbook.ask) == len(v.orderbook.bid) == 10


def test_fake_broker_quote_spread_between_high_low():
    b = FakeBroker()
    symbols = [str(x) for x in range(1001, 1100)]
    quotes = b.quote(symbols, start=100, end=4200, depth=20)
    for k, v in quotes.items():
        assert 100 < v.last_price < 4200
        assert v.low < v.orderbook.ask[0].price < v.high
        assert v.low < v.orderbook.bid[0].price < v.high


def test_fake_broker_order_place_complete():
    b = FakeBroker()
    order = b.order_place()
    assert order.quantity == order.filled_quantity
    assert order.pending_quantity == order.canceled_quantity == 0
    assert order.status == Status.COMPLETE


def test_fake_broker_order_place_canceled():
    b = FakeBroker()
    order = b.order_place(s=Status.CANCELED)
    assert order.quantity == order.canceled_quantity
    assert order.pending_quantity == order.filled_quantity == 0
    assert order.status == Status.CANCELED


def test_fake_broker_order_place_open():
    b = FakeBroker()
    order = b.order_place(s=Status.OPEN)
    assert order.quantity == order.pending_quantity
    assert order.canceled_quantity == order.filled_quantity == 0
    assert order.status == Status.OPEN


def test_fake_broker_order_place_partial_fill():
    b = FakeBroker()
    order = b.order_place(s=Status.PARTIAL_FILL)
    assert order.filled_quantity > 0
    assert order.canceled_quantity > 0
    assert order.pending_quantity == 0
    assert (
        order.filled_quantity + order.canceled_quantity + order.pending_quantity
        == order.quantity
    )
    assert order.status == Status.PARTIAL_FILL


def test_fake_broker_order_place_pending():
    b = FakeBroker()
    order = b.order_place(s=Status.PENDING)
    assert order.filled_quantity > 0
    assert order.pending_quantity > 0
    assert order.canceled_quantity == 0
    assert (
        order.filled_quantity + order.canceled_quantity + order.pending_quantity
        == order.quantity
    )
    assert order.status == Status.PENDING


def test_fake_broker_create_order_args():
    b = FakeBroker()
    order_args = b._create_order_args(**dict())
    for k in ("symbol", "quantity", "price", "side"):
        assert k in order_args
    kwargs = dict(symbol="tsla", quantity=194, trigger_price=200)
    order_args = b._create_order_args(**kwargs)
    for k in ("symbol", "quantity", "price", "side"):
        assert k in order_args
    assert order_args["symbol"] == "tsla"
    assert order_args["quantity"] == 194
    assert order_args["trigger_price"] == 200


def test_fake_broker_order_modify():
    b = FakeBroker()
    order = b.order_modify()
    assert order.status == Status.OPEN
    assert order.pending_quantity == order.quantity
    assert order.filled_quantity == order.canceled_quantity == 0


def test_fake_broker_order_modify_kwargs():
    b = FakeBroker()
    order = b.order_modify(quantity=100, side=-1, order_id="abcd")
    assert order.status == Status.OPEN
    assert order.quantity == 100
    assert order.order_id == "abcd"
    assert order.side == Side.SELL


def test_fake_broker_order_cancel():
    b = FakeBroker()
    order = b.order_cancel()
    assert order.status == Status.CANCELED
    assert order.canceled_quantity == order.quantity
    assert order.pending_quantity == order.filled_quantity == 0


def test_fake_broker_order_cancel_kwargs():
    b = FakeBroker()
    order = b.order_cancel(symbol="amzn", price=188.4)
    assert order.status == Status.CANCELED
    assert order.symbol == "amzn"
    assert order.price == 188.4


def test_fake_broker_positions():
    b = FakeBroker()
    positions = b.positions()
    assert len(positions) > 0


def test_fake_broker_positions_symbols():
    b = FakeBroker()
    symbols = ["tsla", "amzn", "meta"]
    positions = b.positions(symbols=symbols)
    assert len(positions) == 3
    assert set([p.symbol for p in positions]) == set(symbols)


def test_virtual_broker_add_user():
    b = VirtualBroker()
    assert len(b.users) == len(b.clients) == 0
    user1 = VUser(userid="abcd1234")
    user2 = VUser(userid="xyz456")
    assert b.add_user(user1) is True
    assert b.add_user(user2) is True
    assert len(b.users) == len(b.clients) == 2
    assert b.add_user(user1) is False
    assert len(b.users) == len(b.clients) == 2


def test_virtual_broker_order_place_users(basic_broker_with_users):
    b = basic_broker_with_users
    b.failure_rate = 0.0  # To ensure all orders are passed
    b.order_place(symbol="aapl", quantity=10, side=1)
    b.order_place(symbol="goog", quantity=10, side=1)
    for c in b.clients:
        b.order_place(symbol="aapl", quantity=20, side=-1, userid=c)
    b.order_place(symbol="goog", quantity=10, side=1, userid="unknown")
    assert len(b._orders) == 6
    for u in b.users:
        assert len(u.orders) == 1
    assert len(b.clients) == len(b.users) == 3


def test_virtual_broker_order_place_same_memory(basic_broker_with_users):
    # Check orders have the same memory id
    b = basic_broker_with_users
    b.failure_rate = 0.0  # To ensure all orders are passed
    b.order_place(symbol="aapl", quantity=10, side=1)
    b.order_place(symbol="goog", quantity=10, side=1)
    for c in b.clients:
        b.order_place(symbol="aapl", quantity=20, side=-1, userid=c)
    assert len(b._orders) == 5
    for i in range(3):
        order = b.users[i].orders[0]
        assert (id(order)) == id(b._orders[order.order_id])
        assert order is b._orders[order.order_id]


def test_virtual_broker_order_place_delay(basic_broker_with_users):
    b = basic_broker_with_users
    b.order_place(symbol="aapl", quantity=10, side=1)
    b.order_place(symbol="goog", quantity=10, side=1, delay=5e6)
    orders = list(b._orders.values())
    assert orders[0]._delay == 1000000
    assert orders[1]._delay == 5000000


def test_virtual_broker_get_order_by_status(basic_broker_with_users):
    b = basic_broker_with_users
    known = pendulum.datetime(2023, 2, 1, 10, 17)
    with pendulum.travel_to(known):

        resp = b.order_place(symbol="aapl", quantity=10, side=1)
        order_id = resp.data.order_id
        order = b.get(order_id)
        assert order.pending_quantity == 10
    with pendulum.travel_to(known.add(seconds=2)):
        b.get(order_id)
        assert order.status == Status.COMPLETE
        assert order.filled_quantity == 10
    with pendulum.travel_to(known.add(seconds=3)):
        b.get(order_id, status=Status.CANCELED)
        assert order.status == Status.COMPLETE

    # Order with custom status

    with pendulum.travel_to(known):
        resp = b.order_place(symbol="goog", quantity=10, side=1)
        order_id = resp.data.order_id
        order = b.get(order_id)
    with pendulum.travel_to(known.add(seconds=3)):
        b.get(order_id, status=Status.CANCELED)
        assert order.status == Status.CANCELED
        assert order.filled_quantity == 0
        assert order.canceled_quantity == 10


def test_virtual_broker_update_ticker(basic_broker_with_prices):
    b = basic_broker_with_prices
    assert b.tickers["aapl"].ohlc().high == 106
    assert b.tickers["goog"].ohlc().low == 120
    assert b.tickers["amzn"].ohlc().close == 261
    assert b.tickers["aapl"].ohlc().dict() == dict(
        open=100, high=106, low=99, close=103, last_price=103
    )


def test_virtual_broker_ltp(basic_broker_with_prices):
    b = basic_broker_with_prices
    b.ltp("aapl") == dict(aapl=103)
    b.ltp(["goog", "amzn"]) == dict(goog=123, amzn=261)


def test_virtual_broker_ltp(basic_broker_with_prices):
    b = basic_broker_with_prices
    b.ltp("dow") is None
    b.ltp(["goog", "amzn", "dow", "aa"]) == dict(goog=123, amzn=261)
    assert len(b.ltp(["goog", "amzn", "dow", "aa"])) == 2


def test_virtual_broker_ohlc(basic_broker_with_prices):
    b = basic_broker_with_prices
    assert b.ohlc("aapl") == dict(aapl=b.tickers["aapl"].ohlc())


def test_fake_broker_ltp_user_response():
    b = FakeBroker()
    assert b.ltp("aapl", response=4) == 4
    assert b.ltp("aapl", response={1, 2, 3}) == set([1, 2, 3])
    assert b.ltp("aapl", response=dict(price=110)) == {"price": 110}


def test_fake_broker_user_response_other_methods():
    b = FakeBroker()
    assert b.ohlc(response=100) == 100
    assert b.quote(response=100) == 100
    assert b.orderbook(response=100) == 100
    assert b.positions(response=100) == 100
    assert b.orders(response=100) == 100
    assert b.trades(response=100) == 100


def test_fake_broker_user_response_order_methods():
    b = FakeBroker()
    assert b.order_place(response="hello") == "hello"
    assert b.order_modify(response="hello") == "hello"
    assert b.order_cancel(response="hello") == "hello"


def test_fake_broker_orders():
    random.seed(10001)
    b = FakeBroker()
    orders = b.orders()
    assert len(orders) == 6
    assert all([o.price > 0 for o in orders]) is True
    assert all([o.quantity > 0 for o in orders]) is True


def test_fake_broker_trades():
    random.seed(10001)
    b = FakeBroker()
    trades = b.trades()
    assert len(trades) == 12
    assert all([o.price > 0 for o in trades]) is True
    assert all([o.quantity > 0 for o in trades]) is True


def test_replica_broker_defaults():
    broker = ReplicaBroker()
    assert broker.name == "replica"
    assert broker.instruments == dict()
    assert broker.orders == dict()
    assert broker.users == set(["default"])
    assert broker._user_orders == dict()
    assert broker.pending == []
    assert broker.completed == []
    assert broker.fills == []


def test_replica_broker_update():
    broker = ReplicaBroker()
    random.seed(1000)
    names = ["AAPL", "XOM", "DOW"]
    instruments = []
    for name in names:
        inst = generate_instrument(name=name)
        instruments.append(inst)
    broker.update(instruments)
    for name in names:
        assert name in broker.instruments

    # Update existing instrument
    instruments[0].last_price = 144
    broker.update([instruments[0]])
    assert broker.instruments["AAPL"].last_price == 144


def test_replica_broker_order_place(replica_with_instruments):
    known = pendulum.datetime(2023, 4, 1, 9, 30, tz="local")
    broker = replica_with_instruments
    with pendulum.travel_to(known):
        order = broker.order_place(symbol="AAPL", side=1, quantity=10)
        assert order.order_id in broker.orders
        assert len(broker._user_orders["default"]) == 1
        assert order.is_done is False
        assert len(broker.pending) == 1
        assert len(broker.fills) == 1
        assert broker.pending[0].order_id == order.order_id
        assert (
            id(order)
            == id(broker.orders[order.order_id])
            == id(broker._user_orders["default"][0])
            == id(broker.pending[0])
            == id(broker.fills[0].order)
        )

    # Order status should not change with time
    with pendulum.travel_to(known.add(minutes=5)):
        assert order.is_done is False
        assert order.filled_quantity == 0


def test_replica_broker_order_place_multiple_users(replica_with_instruments):
    broker = replica_with_instruments
    order = broker.order_place(symbol="AAPL", side=1, quantity=10)
    for user in ("user1", "user2", "default"):
        order = broker.order_place(symbol="AAPL", side=1, quantity=10, user=user)
    order = broker.order_place(symbol="AAPL", side=1, quantity=10)
    assert len(broker.orders) == 5
    assert len(broker._user_orders) == 3
    for k, v in broker._user_orders.items():
        if k == "default":
            assert len(v) == 3
        else:
            assert len(v) == 1


def test_replica_order_fill(replica_with_orders):
    broker = replica_with_orders
    assert len(broker.orders) == 10
    assert len(broker.completed) == 0
    assert len(broker._user_orders) == 3
    # Since we already knew the filled and non-filled orders
    order_ids = [order.order_id for order in broker.orders.values()]
    filled_ids = []
    non_filled_ids = []
    avg_prices = {
        broker.fills[i].order.order_id: v
        for i, v in zip((0, 3, 4, 5, 7), (125, 136, 136, 153, 153))
    }

    for i, v in enumerate(broker.fills, start=1):
        if i in (2, 3, 7, 9, 10):
            non_filled_ids.append(v.order.order_id)
        else:
            filled_ids.append(v.order.order_id)
    broker.run_fill()
    assert len(broker.completed) == len(broker.fills) == 5
    assert broker.completed
    print(broker.instruments)
    for order in broker.completed:
        assert order.order_id in filled_ids
        assert order.average_price == avg_prices[order.order_id]
    broker.instruments["AAPL"].last_price = 127
    broker.run_fill()
    assert len(broker.fills) == 4
    assert len(broker.completed) == 6
    assert broker.orders[order_ids[1]].average_price == 126
    assert broker.orders[order_ids[1]].filled_quantity == 10
    for i in range(10):
        # results should be the same
        broker.run_fill()
    assert len(broker.fills) == 4
    assert len(broker.completed) == 6
    broker.instruments["AAPL"].last_price = 121.95
    broker.run_fill()
    assert len(broker.fills) == 1
    assert len(broker.completed) == 9
    assert order_ids[6] in broker.orders


def test_replica_broker_order_modify(replica_with_instruments):
    broker = replica_with_instruments
    order = broker.order_place(
        symbol="AAPL", side=1, quantity=10, order_type=2, price=124
    )
    order_id = order.order_id
    broker.run_fill()
    assert order.is_done is False
    broker.order_modify(order_id, quantity=20, price=125.1)
    assert broker.orders[order_id].quantity == 20
    assert broker.orders[order_id].price == 125.1
    broker.run_fill()
    assert order.filled_quantity == 20
    assert order.average_price == 125.1
    assert order.is_done is True


def test_replica_broker_order_modify_market(replica_with_instruments):
    broker = replica_with_instruments
    order = broker.order_place(
        symbol="AAPL", side=1, quantity=10, order_type=2, price=124
    )
    order_id = order.order_id
    broker.run_fill()
    assert order.is_done is False
    broker.order_modify(order_id, quantity=20)
    broker.run_fill()
    assert order.is_done is False
    broker.order_modify(order_id, order_type=1)
    broker.run_fill()
    assert order.filled_quantity == 20
    assert order.average_price == 125
    assert order.is_done is True
    assert (
        id(order)
        == id(broker.orders[order_id])
        == id(broker._user_orders["default"][0])
    )
    assert len(broker.completed) == 1


def test_replica_broker_order_cancel(replica_with_instruments):
    broker = replica_with_instruments
    order = broker.order_place(
        symbol="AAPL", side=1, quantity=10, order_type=2, price=124
    )
    broker.run_fill()
    assert order.is_done is False
    broker.order_cancel(order.order_id)
    assert len(broker.completed) == 1
    assert order.is_done is True
    assert len(broker.fills) == 1
    broker.run_fill()
    assert len(broker.fills) == 0


def test_replica_broker_order_cancel_multiple_times(replica_with_instruments):
    broker = replica_with_instruments
    order = broker.order_place(
        symbol="AAPL", side=1, quantity=10, order_type=2, price=124
    )
    broker.run_fill()
    assert order.is_done is False
    for i in range(10):
        broker.order_cancel(order.order_id)
    assert len(broker.completed) == 1
    assert order.is_done is True
    assert len(broker.fills) == 1
    broker.run_fill()
    assert len(broker.fills) == 0


def test_fake_broker_return_order_id_only():
    broker = FakeBroker(name="faker", return_order_id_only=True)

    response = broker.order_place(symbol="AAPL", side=1, quantity=10)
    assert isinstance(response, str)
    response = broker.order_modify(order_id="some_id", quantity=20)
    assert isinstance(response, str)
    response = broker.order_cancel(order_id="some_order_id")
    assert isinstance(response, str)

    # Return VOrder now
    broker.return_order_id_only = False
    response = broker.order_place(symbol="AAPL", side=1, quantity=10)
    assert isinstance(response, VOrder)
    response = broker.order_modify(order_id="some_id", quantity=20)
    assert isinstance(response, VOrder)
    response = broker.order_cancel(order_id="some_order_id")
    assert isinstance(response, VOrder)
