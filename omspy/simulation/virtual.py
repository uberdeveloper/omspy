import random
import uuid
from typing import Optional, Dict, Set, List, Union, Any
from omspy.models import OrderBook, Quote
from pydantic import BaseModel, PrivateAttr, confloat, ValidationError
from enum import Enum
from collections import defaultdict
from collections.abc import Iterable
from omspy.simulation.models import OrderResponse, VOrder, OHLCV, Side, Status, VQuote


class TickerMode(Enum):
    RANDOM = 1
    MANUAL = 2


def generate_price(start: int = 100, end: int = 110) -> int:
    """
    Generate a random price in the given range between start and end
    start
        starting value
    end
        ending value
    Note
    ----
    1) If the start value is greater than end value, the values are swapped
    """
    if start > end:
        start, end = end, start
    return random.randrange(start, end)


def generate_orderbook(
    bid: float = 100.0,
    ask: float = 100.05,
    depth: int = 5,
    tick: float = 0.01,
    quantity: int = 100,
) -> OrderBook:
    """
    generate a fake orderbook
    bid
        bid price
    ask
        ask price
    depth
        depth of the orderbook
    tick
        difference in price between orders
    quantity
        average quantity of orders per price quote

    Note
    ----
    1) orderbook is generated with a uniform tick difference between subsequent quotes
    2) quantity is averaged between value quantity/2 and quantity * 1.5
    using randrange function
    3) num of orders is randomly picked between 5 to 15
    4) if bid price is greater than ask, the values are swapped
    """
    if bid > ask:
        bid, ask = ask, bid
    asks = []
    bids = []
    q1, q2 = int(quantity * 0.5), int(quantity * 1.5)
    for i in range(depth):
        bid_qty = random.randrange(q1, q2)
        ask_qty = random.randrange(q1, q2)
        b = Quote(
            price=bid - i * tick,
            quantity=bid_qty,
            orders_count=min(random.randrange(5, 15), bid_qty),
        )
        a = Quote(
            price=ask + i * tick,
            quantity=ask_qty,
            orders_count=min(random.randrange(5, 15), ask_qty),
        )
        bids.append(b)
        asks.append(a)
    return OrderBook(ask=asks, bid=bids)


def generate_ohlc(start: int = 100, end: int = 110, volume: int = 1e4):
    """
    Generate random open, high, low, close prices
    start
        start value for price generation
    end
        end value for price generation
    volume
        value for volume
    returns open, high, low, close, last price
    and volume by default
    Note
    ----
    1) ohlc is generated between start and end values
    2) volume is generated based on given value
    """
    if start > end:
        start, end = end, start
    a = random.randrange(start, end)
    b = random.randrange(start, end)
    high, low = max(a, b), min(a, b)
    o = random.randrange(low, high)
    c = random.randrange(low, high)
    ltp = random.randrange(low, high)
    if volume > 0:
        v = random.randrange(int(volume * 0.5), int(volume * 2))
    else:
        v = random.randrange(1000, 200000)
    return OHLCV(open=o, high=high, low=low, close=c, volume=v, last_price=ltp)


class Ticker(BaseModel):
    """
    A simple ticker class to generate fake data
    name
        name for this ticker
    token
        a unique instrument token
    initial_price
        initial_price for the ticker
    ticker_mode
        ticker mode; random or otherwise
    Note
    -----
    1) If ticker mode is random, price is generated based on
    random walk from normal distribution
    """

    name: str
    token: Optional[int] = None
    initial_price: float = 100
    mode: TickerMode = TickerMode.RANDOM
    _high: float = PrivateAttr()
    _low: float = PrivateAttr()
    _ltp: float = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._high = self.initial_price
        self._low = self.initial_price
        self._ltp = self.initial_price

    @property
    def is_random(self) -> bool:
        """
        returns True if the mode is random else False
        """
        return True if self.mode == TickerMode.RANDOM else False

    @property
    def ltp(self) -> float:
        """
        Get the last price and update it
        """
        diff = random.gauss(0, 1) * self._ltp * 0.01
        last_price = self._ltp + diff
        last_price = round(last_price * 20) / 20
        self._ltp = last_price
        self._high = max(self._high, last_price)
        self._low = min(self._low, last_price)
        return self._ltp

    def ohlc(self) -> Dict[str, int]:
        """
        Calculate the ohlc for this ticker
        """
        return dict(
            open=self.initial_price, high=self._high, low=self._low, close=self._ltp
        )


class Client(BaseModel):
    """
    A basic client model
    """

    client_id: str


class FakeBroker(BaseModel):
    """
    A fake instance to generate random stock data
    """

    name: str = "faker"

    def _ltp(self, symbol: str, **kwargs) -> Dict[str, Union[float, int]]:
        """
        get some random last traded price for the instrument
        symbol
            symbol name
        kwargs
            can provide start and end arguments to generate price within the range
        """
        price = generate_price(**kwargs)
        return {symbol: price}

    def ltp(self, symbol: Union[str, Iterable], **kwargs) -> Dict[str, Union[float, int]]:
        """
        get some random last traded price for the given symbols
        symbol
            symbol could be a single symbol or a list of tuple of symbols
        kwargs
            can provide start and end arguments to generate price within the range
        """
        if isinstance(symbol, str):
            return self._ltp(symbol, **kwargs)
        elif isinstance(symbol, Iterable):
            dct = dict()
            for s in symbol:
                dct.update(self._ltp(s, **kwargs))
            return dct


    def orderbook(self, symbol: str, **kwargs) -> Dict[str, OrderBook]:
        """
        generate a random orderbook
        """
        orderbook = generate_orderbook(**kwargs)
        return {symbol: orderbook}

    def ohlc(self, symbol: str, **kwargs) -> Dict[str, OHLCV]:
        """
        generate ohlc prices
        """
        values = generate_ohlc(**kwargs)
        return {symbol: values}

    def quote(self, symbol: str, **kwargs) -> Dict[str, VQuote]:
        """
        generate a detailed quote with ohlcv and orderbook
        start
            start price of the symbol
        end
            end price of the symbol
        volume
            volume for ohlc
        depth
            depth of the orderbook
        tick
            difference in price between orders
        quantity
            average quantity of orders per price quote
        Note
        -----
        1) ask and bid price are derived from start and end prices
        """
        start = kwargs.get("start", 100)
        end = kwargs.get("end", 110)
        volume = kwargs.get("volume", 1e4)
        depth = kwargs.get("depth", 5)
        tick = kwargs.get("tick", 0.01)
        quantity = kwargs.get("quantity", 100)
        ohlc = generate_ohlc(start=start, end=end, volume=volume)
        bid = generate_price(start=ohlc.low, end=ohlc.high)
        ask = bid + tick
        orderbook = generate_orderbook(
            ask=ask, bid=bid, depth=depth, tick=tick, quantity=quantity
        )
        quote = VQuote(orderbook=orderbook, **ohlc.dict())
        return {symbol: quote}

    def order_place(self, **kwargs) -> VOrder:
        """
        Place an order with the broker
        """
        _symbols = [
            "AXP",
            "AAPL",
            "CSCO",
            "PG",
            "V",
            "MMM",
            "JPM",
            "HD",
            "CVX",
            "GS",
            "DOW",
        ]
        symbol = random.choice(_symbols)
        quantity = random.randrange(10, 10000)
        price = random.randrange(1, 1000)
        order_args = dict(
            symbol=symbol,
            side=random.choice([1, -1]),
            price=price,
            quantity=quantity,
            filled_quantity=quantity,
        )
        order_id = uuid.uuid4().hex
        order_args.update(kwargs)
        return VOrder(order_id=order_id, **order_args)


class VirtualBroker(BaseModel):
    """
    A virtual broker instance mimicking a real broker
    """

    name: str = "VBroker"
    tickers: Optional[List[Ticker]]
    clients: Optional[Set[str]]
    failure_rate: confloat(ge=0, le=1) = 0.001
    _orders: defaultdict[str, VOrder] = PrivateAttr()

    class Config:
        validate_assignment = True

    def __init__(self, **data):
        super().__init__(**data)
        self._orders = defaultdict(dict)

    @property
    def is_failure(self) -> bool:
        """
        return whether the response should be a success or failure
        Note
        ----
        1) status is determined based on the failure rate
        """
        num = random.random()
        if num < self.failure_rate:
            return True
        else:
            return False

    def get(self, order_id: str) -> Union[VOrder, None]:
        """
        get the order
        """
        return self._orders.get(order_id)

    def order_place(self, **kwargs) -> Union[OrderResponse, Dict[Any, Any]]:
        if "response" in kwargs:
            return kwargs["response"]
        if self.is_failure:
            return OrderResponse(status="failure", error_message="Unexpected error")
        else:
            order_id = uuid.uuid4().hex
            keys = VOrder.__fields__.keys()
            order_args = dict(order_id=order_id)
            for k, v in kwargs.items():
                if k in keys:
                    order_args[k] = v
            try:
                resp = VOrder(**order_args)
                self._orders[order_args["order_id"]] = resp
                return OrderResponse(status="success", data=resp)
            except ValidationError as e:
                errors = e.errors()
                num = len(errors)
                fld = errors[0].get("loc")[0]
                msg = errors[0].get("msg")
                error_msg = f"Found {num} validation errors; in field {fld} {msg}"
                return OrderResponse(status="failure", error_msg=error_msg)

    def order_modify(
        self, order_id: str, **kwargs
    ) -> Union[OrderResponse, Dict[Any, Any]]:
        if "response" in kwargs:
            return kwargs["response"]
        if self.is_failure:
            return OrderResponse(status="failure", error_message="Unexpected error")
        if order_id not in self._orders:
            return OrderResponse(
                status="failure",
                error_message=f"Order id {order_id} not found on system",
            )
        attribs = ("price", "trigger_price", "quantity")
        modify_args = dict(order_id=order_id)
        order = self.get(order_id)
        for attrib in attribs:
            if attrib in kwargs:
                setattr(order, attrib, kwargs[attrib])
        return OrderResponse(status="success", data=order)

    def order_cancel(
        self, order_id: str, **kwargs
    ) -> Union[OrderResponse, Dict[Any, Any]]:
        if "response" in kwargs:
            return kwargs["response"]
        if self.is_failure:
            return OrderResponse(status="failure", error_message="Unexpected error")
        if order_id not in self._orders:
            return OrderResponse(
                status="failure",
                error_message=f"Order id {order_id} not found on system",
            )
        order = self.get(order_id)
        if order.status == Status.COMPLETE:
            return OrderResponse(
                status="failure", error_message=f"Order {order_id} already completed"
            )
        else:
            order.canceled_quantity = order.quantity - order.filled_quantity
            order.pending_quantity = 0
            return OrderResponse(status="success", data=order)
