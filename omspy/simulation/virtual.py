import random
import uuid
from typing import Optional, Dict, Set, List, Union, Any, Callable
from omspy.models import OrderBook, Quote
from pydantic import BaseModel, PrivateAttr, confloat, ValidationError
from enum import Enum
from collections import defaultdict
from collections.abc import Iterable
from omspy.simulation.models import (
    OrderResponse,
    VOrder,
    OHLCV,
    Side,
    Status,
    VQuote,
    VPosition,
)


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
    _symbols: List[str] = [
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

    def _iterate_method(
        self, method: Callable, symbol: Union[str, Iterable], **kwargs
    ) -> Dict[str, Any]:
        """
        iterate the given method if the symbol is an iterable else return the value
        """
        if isinstance(symbol, str):
            return method(symbol, **kwargs)
        elif isinstance(symbol, Iterable):
            dct = dict()
            for s in symbol:
                dct.update(method(s, **kwargs))
            return dct
        else:
            return dict()

    def _create_order_args(self, **kwargs) -> Dict[str, Any]:
        """
        Create order arguments from the list of
        keyword arguments
        """
        if "symbol" not in kwargs:
            kwargs["symbol"] = random.choice(self._symbols)
        if "quantity" not in kwargs:
            kwargs["quantity"] = random.randrange(10, 10000)
        if "price" not in kwargs:
            kwargs["price"] = random.randrange(1, 1000)
        if "side" not in kwargs:
            kwargs["side"] = random.choice([Side.BUY, Side.SELL])
        return kwargs

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

    def ltp(
        self, symbol: Union[str, Iterable], **kwargs
    ) -> Dict[str, Union[float, int]]:
        """
        get some random last traded price for the given symbols
        symbol
            symbol could be a single symbol or a list of tuple of symbols
        kwargs
            can provide start and end arguments to generate price within the range
        """
        return self._iterate_method(self._ltp, symbol, **kwargs)

    def _orderbook(self, symbol: str, **kwargs) -> Dict[str, OrderBook]:
        """
        generate a random orderbook
        """
        orderbook = generate_orderbook(**kwargs)
        return {symbol: orderbook}

    def orderbook(self, symbol: Union[str, Iterable], **kwargs) -> Dict[str, OrderBook]:
        """
        generate a random orderbook
        symbol
            symbol or list of symbols
        kwargs
            keyword arguments for the generate_orderbook funtion
        """
        return self._iterate_method(self._orderbook, symbol, **kwargs)

    def _ohlc(self, symbol: str, **kwargs) -> Dict[str, OHLCV]:
        """
        generate ohlc prices
        """
        values = generate_ohlc(**kwargs)
        return {symbol: values}

    def ohlc(self, symbol: Union[str, Iterable], **kwargs) -> Dict[str, OHLCV]:
        """
        generate ohlc prices
        symbol
            symbol or list of symbols
        kwargs
            keyword arguments for the generate_ohlc funtion
        """
        return self._iterate_method(self._ohlc, symbol, **kwargs)

    def _quote(self, symbol: str, **kwargs) -> Dict[str, VQuote]:
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

    def quote(self, symbol: Union[str, Iterable], **kwargs) -> Dict[str, VQuote]:
        """
        generate a detailed quote with ohlcv and orderbook
        symbol
            symbol or list of symbols
        list of kwargs
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
        return self._iterate_method(self._quote, symbol, **kwargs)

    def order_place(self, **kwargs) -> VOrder:
        """
        Place an order with the broker
        """
        status: Optional[Status] = kwargs.get("s")
        order_args = self._create_order_args(**kwargs)
        quantity = order_args["quantity"]
        order_args["filled_quantity"] = quantity
        if status:
            if status in (Status.CANCELED, Status.REJECTED):
                order_args.update(dict(filled_quantity=0, canceled_quantity=quantity))
            elif status == Status.OPEN:
                order_args.update(dict(filled_quantity=0, pending_quantity=quantity))
            elif status == Status.PARTIAL_FILL:
                a = random.randrange(1, quantity)
                b = quantity - a
                order_args.update(dict(filled_quantity=a, canceled_quantity=b))
            elif status == Status.PENDING:
                a = random.randrange(1, quantity)
                b = quantity - a
                order_args.update(dict(filled_quantity=a, pending_quantity=b))
        order_id = uuid.uuid4().hex
        order_args.update(kwargs)
        return VOrder(order_id=order_id, **order_args)

    def order_modify(self, **kwargs) -> VOrder:
        """
        Modify an order with the broker
        All orders are returned with status OPEN
        """
        modify_args = self._create_order_args(**kwargs)
        quantity = modify_args["quantity"]
        order_id = modify_args.pop("order_id", uuid.uuid4().hex)
        modify_args["pending_quantity"] = quantity
        return VOrder(order_id=order_id, **modify_args)

    def order_cancel(self, **kwargs) -> VOrder:
        """
        Cancel an order with the broker
        All orders are returned with status CANCELED with
        entire quantity of the orders being CANCELED
        """
        cancel_args = self._create_order_args(**kwargs)
        quantity = cancel_args["quantity"]
        order_id = cancel_args.pop("order_id", uuid.uuid4().hex)
        cancel_args["canceled_quantity"] = quantity
        return VOrder(order_id=order_id, **cancel_args)

    def positions(self, symbols: Optional[List[str]] = None) -> List[VPosition]:
        """
        Generate some fake positions
        symbols
            symbols for which positions are to be generated
        """
        if not symbols:
            n = random.randrange(1, len(self._symbols))
            symbols = random.choices(self._symbols, k=n)
        symbols = set(symbols)  # To remove duplicates
        positions = []
        for symbol in symbols:
            bq = random.randrange(0, 1000)
            sq = random.randrange(0, 1000)
            bv = random.randrange(10, 3000)
            sv = random.randrange(int(bv * 0.5), int(bv * 2))
            position = VPosition(
                symbol=symbol,
                buy_quantity=bq,
                sell_quantity=sq,
                buy_value=bv,
                sell_value=sv,
            )
            positions.append(position)
        return positions


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
        dict(order_id=order_id)
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
