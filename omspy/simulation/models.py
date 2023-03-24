"""
This module contains all the models for running the simulation
All the models start with **V** to indicate virtual models
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Union, Any, Dict, List
from enum import Enum
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
    timestamp: Optional[pendulum.DateTime]
    exchange_order_id: Optional[str]
    exchange_timestamp: Optional[pendulum.DateTime]
    status_message: Optional[str]
    filled_quantity: float = 0
    pending_quantity: float = 0
    canceled_quantity: float = 0

    class Config:
        validate_assignment = True

    def __init__(self, **data):
        super().__init__(**data)
        if self.timestamp is None:
            self.timestamp = pendulum.now(tz="local")
        q = utils.update_quantity(
            q=self.quantity,
            f=self.filled_quantity,
            p=self.pending_quantity,
            c=self.canceled_quantity,
        )
        self.filled_quantity = q.f
        self.pending_quantity = q.p
        self.canceled_quantity = q.c
        if self.average_price is None:
            self.average_price = 0

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
        returns True if it is completed, False if pending
        """
        if self.quantity == self.filled_quantity:
            return True
        elif self.quantity == self.canceled_quantity:
            return True
        elif self.pending_quantity > 0:
            return False
        else:
            return True


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
