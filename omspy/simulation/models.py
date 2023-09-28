"""
This module contains all the models for running the simulation
All the models start with **V** to indicate virtual models
"""

from pydantic import BaseModel, Field, validator, PrivateAttr
from typing import Optional, Union, Any, Dict, List
from enum import Enum
import random
import uuid
import pendulum
import omspy.utils as utils
from omspy.models import OrderBook


class Status(Enum):
    COMPLETE = 1
    REJECTED = 2
    CANCELED = 3
    PARTIAL_FILL = 4  # partially filled but completed order
    OPEN = 5  # all quantity is pending to be filled
    PENDING = 6  # partially filled, waiting to get complete


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"


class Side(Enum):
    BUY = 1
    SELL = -1


class TickerMode(Enum):
    RANDOM = 1
    MANUAL = 2


class OrderType(Enum):
    MARKET = 1
    LIMIT = 2


class OHLC(BaseModel):
    open: float
    high: float
    low: float
    close: float
    last_price: float


class OHLCV(OHLC):
    volume: int


class OHLCVI(OHLCV):
    open_interest: int


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
    orderbook: Optional[OrderBook]
    volume: Optional[int]
    _high: float = PrivateAttr()
    _low: float = PrivateAttr()
    _ltp: float = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._high = self.initial_price
        self._low = self.initial_price
        self._ltp = self.initial_price

    def _update_values(self, last_price: float):
        self._ltp = last_price
        self._high = max(self._high, last_price)
        self._low = min(self._low, last_price)

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
        if self.is_random:
            diff = random.gauss(0, 1) * self._ltp * 0.01
            last_price = self._ltp + diff
            last_price = round(last_price * 20) / 20
            self._update_values(last_price)
        return self._ltp

    def update(self, last_price: float) -> float:
        """
        Update last price,high and low
        """
        self._update_values(last_price)
        return self._ltp

    def ohlc(self) -> OHLC:
        """
        Calculate the ohlc for this ticker
        """
        return OHLC(
            open=self.initial_price,
            high=self._high,
            low=self._low,
            close=self._ltp,
            last_price=self._ltp,
        )


class VQuote(OHLCV):
    orderbook: OrderBook


class VTrade(BaseModel):
    trade_id: str
    order_id: str
    symbol: str
    quantity: int
    price: float
    side: Side
    timestamp: Optional[pendulum.DateTime]

    class Config:
        validate_assignment = True

    @property
    def value(self) -> float:
        return self.side.value * self.quantity * self.price


class VOrder(BaseModel):
    order_id: str
    symbol: str
    quantity: float
    side: Side
    price: Optional[float]
    average_price: Optional[float]
    trigger_price: Optional[float]
    timestamp: Optional[pendulum.DateTime] = None
    exchange_order_id: Optional[str]
    exchange_timestamp: Optional[pendulum.DateTime]
    status_message: Optional[str]
    order_type: OrderType = OrderType.MARKET
    filled_quantity: float = 0
    pending_quantity: float = 0
    canceled_quantity: float = 0
    _delay: int = PrivateAttr()

    class Config:
        validate_assignment = True

    @validator("side", pre=True, always=True)
    def accept_buy_sell_as_side(cls, v):
        if isinstance(v, str):
            if v.lower()[0] == "b":
                return Side.BUY
            elif v.lower()[0] == "s":
                return Side.SELL
            else:
                raise TypeError(f"{v} is not a valid side, should be buy or sell")
        else:
            return v

    @validator("order_type", pre=True, always=True)
    def accept_order_type_as_str(cls, v):
        """
        accept order type as string also and convert it to enum
        should be market or limit
        """
        if isinstance(v, str):
            if v.upper() == "LIMIT":
                return OrderType.LIMIT
            elif v.upper() == "MARKET":
                return OrderType.MARKET
            else:
                raise TypeError(
                    f"{v} is not a valid  order type, should be one of LIMIT/MARKET"
                )
        else:
            return v

    def _make_right_quantity(self):
        """
        Make the pending, filled and canceled correct
        based on available data
        """
        q = utils.update_quantity(
            q=self.quantity,
            f=self.filled_quantity,
            p=self.pending_quantity,
            c=self.canceled_quantity,
        )
        self.filled_quantity = q.f
        self.pending_quantity = q.p
        self.canceled_quantity = q.c

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = pendulum.now(tz="local")
        self._make_right_quantity()
        if self.average_price is None:
            self.average_price = 0
        self._delay = 1e6  # delay in microseconds

    def _modify_order_by_status(self, status: Status):
        """
        Modify an order quantity based on the given status
        """
        if status in (Status.CANCELED, Status.REJECTED):
            self.filled_quantity = 0
            self.pending_quantity = 0
            self.canceled_quantity = self.quantity
        elif status == Status.OPEN:
            self.filled_quantity = 0
            self.pending_quantity = self.pending_quantity
            self.canceled_quantity = 0
        elif status == Status.PARTIAL_FILL:
            a = random.randrange(1, int(self.quantity))
            b = self.quantity - a
            self.filled_quantity = a
            self.pending_quantity = 0
            self.canceled_quantity = b
        elif status == Status.PENDING:
            a = random.randrange(1, int(self.quantity))
            b = self.quantity - a
            self.filled_quantity = a
            self.pending_quantity = b
            self.canceled_quantity = 0
        else:
            self.filled_quantity = self.quantity
            self.pending_quantity = 0
            self.canceled_quantity = 0

    @property
    def is_past_delay(self) -> bool:
        """
        returns True is the order is past delay
        """
        if self.timestamp:
            expiry = self.timestamp.add(microseconds=self._delay)
            return True if pendulum.now(tz="local") > expiry else False
        else:
            return False

    @property
    def status(self) -> Status:
        if self.quantity == self.filled_quantity:
            return Status.COMPLETE
        elif self.quantity == self.canceled_quantity:
            if self.status_message:
                if str(self.status_message).upper().startswith("REJ"):
                    return Status.REJECTED
                else:
                    return Status.CANCELED
            else:
                return Status.CANCELED
        elif self.canceled_quantity > 0:
            if (self.canceled_quantity + self.filled_quantity) == self.quantity:
                return Status.PARTIAL_FILL
            else:
                return Status.PENDING
        elif self.pending_quantity > 0:
            if self.filled_quantity > 0:
                return Status.PENDING
            else:
                return Status.OPEN
        else:
            return Status.OPEN

    @property
    def value(self) -> float:
        """
        returns the value of the order
        negative means sell and positive means buy
        """
        if not self.average_price:
            if not self.price:
                average_price = 0.0
            else:
                average_price = self.price
        else:
            average_price = self.average_price
        return self.side.value * self.filled_quantity * average_price

    @property
    def is_done(self) -> bool:
        """
        whether the order is finished either by fully filled
        or canceled
        returns True if it is done, False if pending
        """
        if self.quantity == self.filled_quantity:
            return True
        elif self.quantity == self.canceled_quantity:
            return True
        elif self.pending_quantity > 0:
            return False
        else:
            return True

    @property
    def is_complete(self) -> bool:
        """
        returns True if the entire order is completely filled
        else False
        """
        if self.quantity == self.filled_quantity:
            return True
        elif self.status == Status.COMPLETE:
            return True
        else:
            return False

    def modify_by_status(self, status: Status = Status.COMPLETE) -> bool:
        """
        Modify order by status
        returns True if the order is modified else False
        """
        if self.is_done:
            return False
        if self.is_past_delay:
            self._modify_order_by_status(status)
            return True
        else:
            return False

    def set_exchange_order_id(self):
        if not (self.exchange_order_id):
            self.exchange_order_id = uuid.uuid4().hex

    def set_exchange_timestamp(self):
        print(pendulum.now())
        if not (self.exchange_timestamp):
            print(pendulum.now())
            self.exchange_timestamp = pendulum.now(tz="local")


class VPosition(BaseModel):
    symbol: str
    buy_quantity: Optional[Union[int, float]]
    sell_quantity: Optional[Union[int, float]]
    buy_value: Optional[float]
    sell_value: Optional[float]

    class Config:
        validate_assignment = True

    @property
    def average_buy_price(self) -> float:
        """
        Get the average buy price
        returns 0 if there is no price or quantity
        """
        if self.buy_quantity and self.buy_value:
            return self.buy_value / self.buy_quantity
        else:
            return 0.0

    @property
    def average_sell_price(self) -> float:
        """
        Get the average sell price
        returns 0 if there is no price or quantity
        """
        if self.sell_quantity and self.sell_value:
            return self.sell_value / self.sell_quantity
        else:
            return 0.0

    @property
    def net_quantity(self) -> float:
        """
        Get the net quantity for the position
        negative indicates sell and positive indicates sell
        """
        buy_qty = self.buy_quantity if self.buy_quantity else 0
        sell_qty = self.sell_quantity if self.sell_quantity else 0
        return buy_qty - sell_qty

    @property
    def net_value(self) -> float:
        """
        Get the net value for the position
        negative indicates a net sell value and positive indicates a net buy value
        """
        buy_value = self.buy_value if self.buy_value else 0
        sell_value = self.sell_value if self.sell_value else 0
        return buy_value - sell_value


class VUser(BaseModel):
    userid: str
    name: Optional[str]
    orders: List[VOrder] = Field(default_factory=list)

    @validator("userid")
    def userid_should_be_upper(cls, v):
        return str(v).upper()

    def add(self, order: VOrder):
        """
        add an order to the user
        """
        self.orders.append(order)


class Response(BaseModel):
    status: ResponseStatus
    timestamp: Optional[pendulum.DateTime] = None

    class Config:
        validate_assignment = True

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = pendulum.now(tz="local")


class OrderResponse(Response):
    error_msg: Optional[str] = None
    data: Optional[VOrder] = None

    class Config:
        validate_assignment = True


class AuthResponse(Response):
    user_id: str
    message: str = "Authentication successful"


class GenericResponse(OrderResponse):
    data: Optional[Any]


class LTPResponse(GenericResponse):
    data: Dict[str, Union[int, float]]


class OHLCVResponse(GenericResponse):
    data: Dict[str, OHLCV]


class QuoteResponse(GenericResponse):
    data: Dict[str, VQuote]


class OrderBookResponse(GenericResponse):
    data: Dict[str, OrderBook]


class PositionResponse(GenericResponse):
    data: List[VPosition]


class Instrument(BaseModel):
    """
    Instrument containing data
    """

    name: str
    token: Optional[int] = None
    last_price: float
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float]
    open_interest: Optional[float]
    strike: Optional[float]
    expiry: Optional[pendulum.Date]
    orderbook: Optional[OrderBook]
    last_update_time: Optional[pendulum.DateTime]


class OrderFill(BaseModel):
    """
    A simple order fill model
    """

    order: VOrder
    last_price: float

    def __init__(self, **data):
        super().__init__(**data)
        self.order: VOrder = data["order"]
        self._as_market()

    @property
    def done(self):
        return self.order.is_done

    def _as_market(self):
        """
        Update order if the limit price behaves like a MARKET order
        So, if the last price is 120 and a BUY order is sent for 122, the order would be filled at 120
        """
        side = self.order.side
        price = self.order.price
        order_type = self.order.order_type
        ltp = self.last_price
        if order_type == OrderType.LIMIT:
            if side == Side.BUY:
                if price > ltp:
                    self.order.filled_quantity = self.order.quantity
                    self.order.average_price = self.last_price
            elif side == Side.SELL:
                if price < ltp:
                    self.order.filled_quantity = self.order.quantity
                    self.order.average_price = self.last_price
            self.order._make_right_quantity()

    def update(self, last_price: float = None):
        """
        update order
        """
        # Do nothing if order is complete
        if self.order.is_done:
            return
        last_price = last_price or self.last_price
        order = self.order
        side = order.side
        order_type = order.order_type
        if order_type == OrderType.MARKET:
            order.price = last_price
            order.average_price = last_price
            order.filled_quantity = order.quantity
            order._make_right_quantity()
        elif order_type == OrderType.LIMIT:
            if side == Side.BUY:
                if last_price < order.price:
                    order.average_price = order.price
                    order.filled_quantity = order.quantity
                    order._make_right_quantity()
            elif side == Side.SELL:
                if last_price > order.price:
                    order.average_price = order.price
                    order.filled_quantity = order.quantity
                    order._make_right_quantity()
