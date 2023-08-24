import random
import uuid
import logging
from functools import wraps
from typing import Optional, Dict, Set, List, Union, Any, Callable
from omspy.models import OrderBook, Quote
from pydantic import BaseModel, PrivateAttr, confloat, ValidationError, Field
from enum import Enum
from collections import defaultdict
from collections.abc import Iterable
from omspy.simulation.models import (
    OrderResponse,
    ResponseStatus,
    VOrder,
    VTrade,
    OHLCV,
    Side,
    Status,
    VQuote,
    VPosition,
    VUser,
    TickerMode,
    Ticker,
    Instrument,
    OrderFill,
)

SUCCESS = ResponseStatus.SUCCESS
FAILURE = ResponseStatus.FAILURE


def user_response(f: Callable):
    """
    override a function with the response provided by the user
    if the user includes the `response` keyword,
    user response would be returns instead of the function response
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        if "response" in kwargs:
            return kwargs.pop("response")
        else:
            return f(*args, **kwargs)

    return wrapper


def _iterate_method(
    method: Callable, symbol: Union[str, Iterable], **kwargs
) -> Dict[str, Any]:
    """
    iterate the given method if the symbol is an iterable else return the value
    """
    if isinstance(symbol, str):
        return method(symbol, **kwargs)
    elif isinstance(symbol, Iterable):
        dct = dict()
        for s in symbol:
            val = method(s, **kwargs)
            if val:
                dct.update(val)
        return dct
    else:
        return dict()


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


def generate_ohlc(start: int = 100, end: int = 110, volume: int = 10000) -> OHLCV:
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

    def _get_random_symbols(self, n: Optional[int] = None) -> List[str]:
        """
        get random symbols
        """
        if n is None:
            n = random.randrange(1, len(self._symbols))
        symbols = random.choices(self._symbols, k=n)
        return symbols

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

    @user_response
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
        return _iterate_method(self._ltp, symbol, **kwargs)

    def _orderbook(self, symbol: str, **kwargs) -> Dict[str, OrderBook]:
        """
        generate a random orderbook
        """
        orderbook = generate_orderbook(**kwargs)
        return {symbol: orderbook}

    @user_response
    def orderbook(self, symbol: Union[str, Iterable], **kwargs) -> Dict[str, OrderBook]:
        """
        generate a random orderbook
        symbol
            symbol or list of symbols
        kwargs
            keyword arguments for the generate_orderbook funtion
        """
        return _iterate_method(self._orderbook, symbol, **kwargs)

    def _ohlc(self, symbol: str, **kwargs) -> Dict[str, OHLCV]:
        """
        generate ohlc prices
        """
        values = generate_ohlc(**kwargs)
        return {symbol: values}

    @user_response
    def ohlc(self, symbol: Union[str, Iterable], **kwargs) -> Dict[str, OHLCV]:
        """
        generate ohlc prices
        symbol
            symbol or list of symbols
        kwargs
            keyword arguments for the generate_ohlc funtion
        """
        return _iterate_method(self._ohlc, symbol, **kwargs)

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
        bid = generate_price(start=int(ohlc.low), end=int(ohlc.high))
        ask = bid + tick
        orderbook = generate_orderbook(
            ask=ask, bid=bid, depth=depth, tick=tick, quantity=quantity
        )
        quote = VQuote(orderbook=orderbook, **ohlc.dict())
        return {symbol: quote}

    @user_response
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
        return _iterate_method(self._quote, symbol, **kwargs)

    @user_response
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

    @user_response
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

    @user_response
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

    @user_response
    def positions(self, symbols: Optional[List[str]] = None) -> List[VPosition]:
        """
        Generate some fake positions
        symbols
            symbols for which positions are to be generated
        """
        if not symbols:
            n = random.randrange(1, len(self._symbols))
            symbols = random.choices(self._symbols, k=n)
        symbols = list(set(symbols))  # To remove duplicates
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

    @user_response
    def orders(self, symbols: Optional[List[str]] = None) -> List[VOrder]:
        """
        Generate some fake orders
        symbols
            symbol for which fake orders are to be generated
        """
        if not symbols:
            symbols = self._get_random_symbols()
        orders = []
        for symbol in symbols:
            order_id = uuid.uuid4().hex
            quantity = random.randrange(10, 100)
            price = round(random.random() * random.randrange(10, 100), 2)
            order = VOrder(
                order_id=order_id,
                symbol=symbol,
                quantity=quantity,
                filled_quantity=quantity,
                side=random.choice(list(Side)),
                price=price,
                average_price=price,
            )
            orders.append(order)
        return orders

    @user_response
    def trades(self, symbols: Optional[List[str]] = None) -> List[VTrade]:
        """
        Generate some fake trades
        symbols
            symbol for which fake trades are to be generated
        """
        if not symbols:
            n = random.randrange(1, len(self._symbols)) * 2
            symbols = self._get_random_symbols(n)
        trades = []
        for symbol in symbols:
            order_id = uuid.uuid4().hex
            trade_id = uuid.uuid4().hex
            quantity = random.randrange(10, 100)
            price = round(random.random() * random.randrange(10, 100), 2)
            trade = VTrade(
                trade_id=trade_id,
                order_id=order_id,
                symbol=symbol,
                quantity=quantity,
                side=random.choice(list(Side)),
                price=price,
            )
            trades.append(trade)
        return trades


class VirtualBroker(BaseModel):
    """
    A virtual broker instance mimicking a real broker
    name
        name to identify this broker
    tickers
        list of stock tickers
    users
        list of users
    failure_rate
        the failure rate for responses
    """

    name: str = "VBroker"
    tickers: Dict[str, Ticker] = Field(default_factory=dict)
    users: List[VUser] = Field(default_factory=list)
    failure_rate: float = Field(ge=0, le=1, default=0.001)
    _orders: Dict[str, VOrder] = PrivateAttr()
    _clients: Set[str] = PrivateAttr()
    _delay: int = PrivateAttr()  # delay in microseconds for updating orders

    class Config:
        validate_assignment = True

    def __init__(self, **data):
        super().__init__(**data)
        self._orders = defaultdict(list)
        self._clients = set()
        self._delay = 1e6

    @property
    def clients(self) -> Set[str]:
        return self._clients

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

    def get(
        self, order_id: str, status: Status = Status.COMPLETE
    ) -> Union[VOrder, None]:
        """
        get the order
        """
        order: VOrder = self._orders.get(order_id)
        if order:
            order.modify_by_status(status)
            return order
        else:
            return None

    def add_user(self, user: VUser) -> bool:
        """
        add a new user
        returns True if an user is added successfully else False
        """
        if user.userid in self.clients:
            logging.warning(f"User {user.userid} already exists")
            return False
        else:
            self._clients.add(user.userid)
            self.users.append(user)
            return True

    def order_place(self, **kwargs) -> Union[OrderResponse, Dict[Any, Any]]:
        if "response" in kwargs:
            return kwargs["response"]
        if self.is_failure:
            return OrderResponse(status=FAILURE, error_msg="Unexpected error")
        else:
            order_id = uuid.uuid4().hex
            keys = VOrder.__fields__.keys()
            order_args = dict(order_id=order_id)
            is_user: bool = False
            userid: Optional[str] = None
            delay: int = self._delay
            for k, v in kwargs.items():
                if k == "userid":
                    userid = str(v).upper()
                    if userid in self.clients:
                        is_user = True
                if k == "delay":
                    delay = v
                elif k in keys:
                    order_args[k] = v
            try:
                resp = VOrder(**order_args)
                resp._delay = delay
                self._orders[order_args["order_id"]] = resp
                if is_user:
                    for user in self.users:
                        if user.userid == userid:
                            user.orders.append(resp)
                            break
                return OrderResponse(status=SUCCESS, data=resp)
            except ValidationError as e:
                errors: List = e.errors()
                num = len(errors)
                fld = errors[0].get("loc")[0]
                msg = errors[0].get("msg")
                error_msg = f"Found {num} validation errors; in field {fld} {msg}"
                return OrderResponse(status=FAILURE, error_msg=error_msg)

    def order_modify(
        self, order_id: str, **kwargs
    ) -> Union[OrderResponse, Dict[Any, Any]]:
        if "response" in kwargs:
            return kwargs["response"]
        if self.is_failure:
            return OrderResponse(status=FAILURE, error_msg="Unexpected error")
        if order_id not in self._orders:
            return OrderResponse(
                status=FAILURE,
                error_msg=f"Order id {order_id} not found on system",
            )
        attribs = ("price", "trigger_price", "quantity")
        dict(order_id=order_id)
        order = self.get(order_id)
        for attrib in attribs:
            if attrib in kwargs:
                setattr(order, attrib, kwargs[attrib])
        return OrderResponse(status=SUCCESS, data=order)

    def order_cancel(
        self, order_id: str, **kwargs
    ) -> Union[OrderResponse, Dict[Any, Any]]:
        if "response" in kwargs:
            return kwargs["response"]
        if self.is_failure:
            return OrderResponse(status=FAILURE, error_msg="Unexpected error")
        if order_id not in self._orders:
            return OrderResponse(
                status=FAILURE,
                error_msg=f"Order id {order_id} not found on system",
            )
        order = self.get(order_id)
        if order:
            if order.status == Status.COMPLETE:
                return OrderResponse(
                    status=FAILURE, error_msg=f"Order {order_id} already completed"
                )
            else:
                order.canceled_quantity = order.quantity - order.filled_quantity
                order.pending_quantity = 0
                return OrderResponse(status=SUCCESS, data=order)
        else:
            return OrderResponse(
                status=FAILURE,
                error_msg=f"Order id {order_id} not found on system",
            )

    def update_tickers(self, last_price: Dict[str, float]):
        """
        update tickers
        last_price
            dictionary of last traded price with key being
            the symbol name and value the last price
        """
        for k, v in last_price.items():
            ticker = self.tickers.get(k)
            if ticker:
                ticker.update(v)

    def _ltp(self, symbol: str) -> Optional[Dict[str, float]]:
        """
        get last traded price for a symbol
        """
        ticker = self.tickers.get(symbol)
        if ticker:
            return {symbol: ticker.ltp}
        else:
            return None

    def ltp(self, symbol: Union[str, Iterable]) -> Optional[Dict[str, float]]:
        """
        Get last traded prices for the given list of symbols
        """
        return _iterate_method(self._ltp, symbol)

    def _ohlc(self, symbol: str) -> Optional[Dict[str, OHLCV]]:
        ticker = self.tickers.get(symbol)
        if ticker:
            return {symbol: ticker.ohlc()}
        else:
            return None

    def ohlc(self, symbol: Union[str, Iterable]) -> Optional[Dict[str, OHLCV]]:
        """
        Get OHLC prices
        """
        return _iterate_method(self._ohlc, symbol)

    def _quote(self, symbol: str) -> Optional[Dict[str, VQuote]]:
        """
        return the quote for the symbol
        """
        ticker = self.tickers.get(symbol)
        if ticker:
            if ticker.orderbook:
                quote = VQuote(orderbook=ticker.orderbook, **ticker.ohlc().dict())
                return {symbol: quote}
            else:
                return None
        else:
            return None

    def quote(self, symbol: Union[str, Iterable]) -> Optional[Dict[str, VQuote]]:
        """
        return the quote for the symbol or list of symbols
        """
        return _iterate_method(self._quote, symbol)


class ReplicaBroker(BaseModel):
    """
    Replica Broker for simulation real brokers
    """

    name: str = "replica"
    instruments: Dict[str, Instrument] = Field(default_factory=defaultdict)
    orders: Dict[str, VOrder] = Field(default_factory=defaultdict)
    users: set[str] = Field(default_factory=set)
    pending: List[VOrder] = Field(default_factory=list)
    completed: List[VOrder] = Field(default_factory=list)
    fills: List[OrderFill] = Field(default_factory=list)
    _user_orders: Dict[str, List[VOrder]] = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self.users.add("default")
        self._user_orders = defaultdict(list)

    def update(self, instruments: List[Instrument]):
        """
        update the given list of instruments
        Note
        -----
        1) The instruments are directly updated and any
        existing data is overwritten
        """
        for inst in instruments:
            name = inst.name
            self.instruments[name] = inst

    def order_place(self, **kwargs) -> VOrder:
        """
        Place an order with the broker
        """
        user = kwargs.pop("user", "default")
        order_id = uuid.uuid4().hex
        order = VOrder(order_id=order_id, **kwargs)
        self._user_orders[user].append(order)
        self.orders[order_id] = order
        self.pending.append(order)

        symbol = order.symbol
        last_price = self.instruments[symbol].last_price
        fill = OrderFill(order=order, last_price=last_price)
        self.fills.append(fill)
        return order

    def order_modify(self, order_id: str, **kwargs) -> VOrder:
        """
        Modify an order with the broker
        """
        order = self.orders[order_id]
        for k, v in kwargs.items():
            if hasattr(order, k):
                setattr(order, k, v)
        return order

    def order_cancel(self, order_id: str) -> VOrder:
        """
        Cancel an existing order
        """
        order = self.orders[order_id]
        if not (order.is_done):
            order.canceled_quantity = order.quantity - order.filled_quantity
            self.completed.append(order)
        return order

    def run_fill(self):
        """
        run order fill for the existing pending orders
        """
        if len(self.fills) == 0:
            logging.info("No order to fill")
        orders_done = set()
        for i, fill in enumerate(self.fills):
            symbol = fill.order.symbol
            last_price = self.instruments[symbol].last_price
            if last_price:
                fill.last_price = last_price
                fill.update()
                if fill.done:
                    orders_done.add(fill.order.order_id)
            else:
                logging.warning(f"Instrument not found for ticker {symbol}")

        # Clean completed orders
        if len(orders_done) > 0:
            for order_id in orders_done:
                comp = self.orders[order_id]
                self.completed.append(comp)
        self.fills = [fill for fill in self.fills if not (fill.done)]
