"""
This module contains the list of basic models
"""
from pydantic import BaseModel, validator
from typing import Optional, List
import pendulum


class QuantityMatch(BaseModel):
    buy: int = 0
    sell: int = 0

    @property
    def is_equal(self) -> bool:
        return True if self.buy == self.sell else False

    @property
    def not_matched(self) -> int:
        return self.buy - self.sell


class BasicPosition(BaseModel):
    """
    A simple position tracking mechanism
    """

    symbol: str
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_value: float = 0.0
    sell_value: float = 0.0

    @property
    def net_quantity(self) -> int:
        return self.buy_quantity - self.sell_quantity

    @property
    def average_buy_value(self) -> float:
        return self.buy_value / self.buy_quantity if self.buy_value > 0.0 else 0.0

    @property
    def average_sell_value(self) -> float:
        return self.sell_value / self.sell_quantity if self.sell_quantity > 0 else 0.0


class Quote(BaseModel):
    price: float
    quantity: int
    orders: Optional[int] = None

    @property
    def value(self):
        return self.price * self.quantity


class OrderBook(BaseModel):
    bid: List[Quote]
    ask: List[Quote]


class Tracker(BaseModel):
    """
    A simple tracker to track the high low prices
    """

    name: str  # name of the symbol to be tracked
    last_price: float = 0
    # Initializing high and low to extreme values
    high: float = -1e100
    low: float = 1e100

    def update(self, last_price: float):
        self.last_price = last_price
        self.high = max(last_price, self.high)
        self.low = min(last_price, self.low)


class Timer(BaseModel):
    """
    A simple timer that could be attached to any model
    """

    start_time: pendulum.DateTime
    end_time: pendulum.DateTime
    timezone: Optional[str] = None

    @validator("end_time")
    def validate_times(cls, v, values):
        """
        Validate end_time greater than start_time
        and start_time greater than current time
        """
        start = values.get("start_time")
        tz = values.get("timezone")
        if v < start:
            raise ValueError("end time greater than start time")
        if start < pendulum.now(tz=tz):
            raise ValueError("start time lesser than current time")
        return v

    @property
    def has_started(self):
        """
        Whether tracking has started
        """
        return True if pendulum.now(tz=self.timezone) > self.start_time else False

    @property
    def has_completed(self):
        """
        Whether tracking has completed
        """
        return True if pendulum.now(tz=self.timezone) > self.end_time else False

class TimeTracker(Tracker, Timer):
    pass
