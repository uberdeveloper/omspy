"""
This module contains the list of basic models
"""
from pydantic import BaseModel, validator, PrivateAttr
from typing import Optional, List, Union
from copy import deepcopy
import pendulum
import logging


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
    orders_count: Optional[int] = None

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
    def has_started(self) -> bool:
        """
        Whether tracking has started
        """
        return True if pendulum.now(tz=self.timezone) > self.start_time else False

    @property
    def has_completed(self) -> bool:
        """
        Whether tracking has completed
        """
        return True if pendulum.now(tz=self.timezone) > self.end_time else False

    @property
    def is_running(self) -> bool:
        """
        Whether the timer is in progress
        returns True if it has started and not completed
        else False
        """
        if self.has_started and not self.has_completed:
            return True
        else:
            return False


class TimeTracker(Tracker, Timer):
    pass


class OrderLock(BaseModel):
    """
    Lock order placement, modification and cancellation
    for a few seconds
    """

    max_order_creation_lock_time: float = 60
    max_order_modification_lock_time: float = 60
    max_order_cancellation_lock_time: float = 60
    timezone: Optional[str] = None
    _creation_lock_till: pendulum.DateTime = PrivateAttr()
    _modification_lock_till: pendulum.DateTime = PrivateAttr()
    _cancellation_lock_till: pendulum.DateTime = PrivateAttr()

    def __init__(self, **data):
        super().__init__(**data)
        self._creation_lock_till = pendulum.now(tz=self.timezone)
        self._modification_lock_till = pendulum.now(tz=self.timezone)
        self._cancellation_lock_till = pendulum.now(tz=self.timezone)

    @property
    def creation_lock_till(self):
        return self._creation_lock_till

    @property
    def modification_lock_till(self):
        return self._modification_lock_till

    @property
    def cancellation_lock_till(self):
        return self._cancellation_lock_till

    def create(self, seconds: float) -> pendulum.DateTime:
        """
        Lock the create_order function for the given number of seconds
        """
        seconds = min(seconds, self.max_order_creation_lock_time)
        self._creation_lock_till = pendulum.now(tz=self.timezone).add(
            seconds=int(seconds)
        )
        return self.creation_lock_till

    def modify(self, seconds: float) -> pendulum.DateTime:
        """
        Lock the modify_order function for the given number of seconds
        """
        seconds = min(seconds, self.max_order_modification_lock_time)
        self._modification_lock_till = pendulum.now(tz=self.timezone).add(
            seconds=int(seconds)
        )
        return self.modification_lock_till

    def cancel(self, seconds: float) -> pendulum.DateTime:
        """
        Lock the cancel_order function for the given number of seconds
        """
        seconds = min(seconds, self.max_order_cancellation_lock_time)
        self._cancellation_lock_till = pendulum.now(tz=self.timezone).add(
            seconds=int(seconds)
        )
        return self.cancellation_lock_till

    @property
    def can_create(self) -> bool:
        """
        returns True if order can be created else False
        """
        return (
            True if pendulum.now(tz=self.timezone) > self.creation_lock_till else False
        )

    @property
    def can_modify(self) -> bool:
        """
        returns True if order can be modified else False
        """
        return (
            True
            if pendulum.now(tz=self.timezone) > self.modification_lock_till
            else False
        )

    @property
    def can_cancel(self) -> bool:
        """
        returns True is order can be canceled else False
        """
        return (
            True
            if pendulum.now(tz=self.timezone) > self.cancellation_lock_till
            else False
        )


class Candle(BaseModel):
    """
    A model representing a single candle
    """

    timestamp: pendulum.DateTime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float]
    info: Optional[str]


class CandleStick(BaseModel):
    """
    Class to work on candlesticks
    """

    symbol: str
    candles: List[Candle] = []
    initial_price: float = 0
    interval: int = 300  # in seconds
    timer: Optional[Timer] = None
    timezone: Optional[str] = "local"
    ltp: float = 0
    high: float = -1e100  # Initialize to a impossible value
    low: float = 1e100  # Initialize to a impossible value
    bar_open: float = 0
    bar_high: float = -1e100  # Initialize to a impossible value
    bar_low: float = 1e100  # Initialize to a impossible value
    next_interval: Optional[pendulum.DateTime] = None
    periods: List[pendulum.DateTime] = []
    _last_ltp: float = PrivateAttr()  # to track bar close price

    class Config:
        underscore_attribs_are_private = True

    def __init__(self, **data) -> None:
        super().__init__(**data)
        self._last_ltp = 0
        if self.timer is None:
            timer = Timer(
                start_time=pendulum.today(tz=self.timezone).add(hours=9, minutes=15),
                end_time=pendulum.today(tz=self.timezone).add(hours=15, minutes=30),
            )
            self.timer = timer
        period = pendulum.period(self.timer.start_time, self.timer.end_time)
        for p in period.range("seconds", self.interval):
            self.periods.append(p)
        # The first period is popped since it is the start
        self.periods.pop(0)
        if self.next_interval is None:
            self.next_interval = self.periods.pop(0)

    def add_candle(self, candle: Candle) -> None:
        """
        Add a candle
        """
        self.candles.append(deepcopy(candle))

    def _update_prices(self):
        """
        Update running candle
        """
        ltp = self.ltp
        if self.initial_price == 0:
            self.initial_price = ltp
        if self.bar_open == 0:
            self.bar_open = ltp
        self.bar_high = max(self.bar_high, ltp)
        self.bar_low = min(self.bar_low, ltp)
        self.high = max(self.high, ltp)
        self.low = min(self.low, ltp)

    def update_candle(self, timestamp: pendulum.DateTime = pendulum.now()) -> Candle:
        """
        Update and append the existing candle
        returns the updated candle
        """
        if len(self.candles) == 0:
            open_price = self.initial_price
        else:
            open_price = self.bar_open
        candle = Candle(
            timestamp=timestamp,
            open=open_price,
            high=self.bar_high,
            low=self.bar_low,
            close=self._last_ltp,
        )
        self.add_candle(candle)
        self.bar_high = -1e100
        self.bar_low = 1e100
        self.bar_open = 0
        self._update_prices()
        return candle

    @property
    def bullish_bars(self) -> int:
        """
        Returns the number of bullish bars
        """
        count = 0
        for candle in self.candles:
            if candle.close > candle.open:
                count += 1
        return count

    @property
    def bearish_bars(self) -> int:
        """
        Returns the number of bullish bars
        """
        count = 0
        for candle in self.candles:
            if candle.close < candle.open:
                count += 1
        return count

    def get_next_interval(self) -> Union[pendulum.DateTime, None]:
        """
        Get the next time interval
        returns None if all intervals are completed
        """
        if len(self.periods) == 0:
            return None
        to_remove = []
        period = None
        for p in self.periods:
            if p > pendulum.now(tz=self.timezone):
                period = p
                to_remove.append(p)
                break
            else:
                to_remove.append(p)
        for p in to_remove:
            try:
                self.periods.remove(p)
            except ValueError:
                logging.error(f"Period {period} cannot be found in the list of periods")
        return period

    def update(self, ltp: float) -> None:
        if self.timer.is_running:
            self._last_ltp = self.ltp
            self.ltp = ltp
            now = pendulum.now(tz=self.timezone)
            if now > self.next_interval:
                self.update_candle(timestamp=self.next_interval)
                self.next_interval = self.get_next_interval()
            else:
                self._update_prices()

    @property
    def last_bullish_bar_index(self) -> int:
        """
        Get the index of the last bullish bar candle
        """
        l = len(self.candles)
        if l == 0:
            return 0
        for i, candle in enumerate(reversed(self.candles)):
            if candle.close > candle.open:
                return l - i
        # If no bullish candle
        return 0

    @property
    def last_bearish_bar_index(self) -> int:
        """
        Get the index of the last bullish bar candle
        """
        l = len(self.candles)
        if l == 0:
            return 0
        for i, candle in enumerate(reversed(self.candles)):
            if candle.close < candle.open:
                return l - i
        # If no bearish candle
        return 0

    @property
    def last_bullish_bar(self) -> Union[Candle, None]:
        """
        Return the latest bullish bar
        """
        l = len(self.candles)
        if l == 0:
            return
        i = self.last_bullish_bar_index
        if i == 0:
            return
        else:
            return self.candles[i - 1]

    @property
    def last_bearish_bar(self) -> Union[Candle, None]:
        """
        Return the latest bearish bar
        """
        l = len(self.candles)
        if l == 0:
            return
        i = self.last_bearish_bar_index
        if i == 0:
            return
        else:
            return self.candles[i - 1]
