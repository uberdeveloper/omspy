import pendulum
from omspy.order import Order, CompoundOrder
from pydantic import BaseModel, PrivateAttr, Field
from sqlite_utils import Database
from typing import Optional, Any, NamedTuple
from collections import namedtuple

trailing_values = namedtuple("trailing", ["stop", "target"], defaults=[None, None])


class TrailingResult(NamedTuple):
    done: bool
    stop: Optional[float] = None
    target: Optional[float] = None
    next_trail_at: Optional[float] = None


def _get_trailing_stop_by_percent(
    max_mtm: float, trailing_percent: float, trailing_step: Optional[float] = None
) -> float:
    """
    max_mtm
        max_mtm hit
    trailing_percent
        trailing_percentage, pass 10 percent as 10
    trailing_step
        optional trailing step as absolute value
    """
    # TODO: Handle percentages greater than 100
    if trailing_step:
        m = (max_mtm // trailing_step) * trailing_step
        calc = m * (1 - (trailing_percent / 100))
        if calc >= 0:
            return max(calc, trailing_step)
        else:
            return calc + trailing_step * 0.5
    else:
        return max_mtm * (1 - (trailing_percent / 100))


def _get_trailing_stop_by_mtm(
    max_mtm: float, trailing_mtm: float, trailing_step: Optional[float] = None
) -> float:
    """
    get the trailing stop by mtm value
    max_mtm
        max mtm hit
    trailing_mtm
        trailing value of mtm, this is the mtm at which trailing is reset
    trailing_step
        optional trailing step, this is the distance to be maintained between max_mtm and trailing stop
    Note
    -----
    1) If trailing_step is not given, trailing_stop will be max_mtm - trailing_mtm
    2) If trailing_step is greater than trailing mtm, then trailing_stop will be trailing_step
    """
    if trailing_step:
        m = (max_mtm // trailing_step) * trailing_step
        if max_mtm >= 0:
            return max(m - trailing_mtm, trailing_step)
        else:
            return m + trailing_mtm + trailing_step
    return max_mtm - trailing_mtm if max_mtm >= 0 else max_mtm + trailing_mtm


def get_trailing_stop_and_target(
    last_price: float,
    max_mtm: float,
    min_mtm: float,
    target: Optional[float] = None,
    trailing_stop: Optional[float] = None,
    trailing_percent: Optional[float] = None,
    trailing_mtm: Optional[float] = None,
    trailing_step: Optional[float] = None,
    start_trailing_at: Optional[float] = None,
) -> trailing_values:
    """
    Get trailing stop and target value based on the given parameters
    last_price
        last traded price of the instrument
    max_mtm
        maximum mtm hit
    min_mtm
        minimum mtm hit
    target
        target value to exit
    trailing_stop
        the initial trailing stop value
    trailing_percent
        trailing percent from mtm; specify 10 percent as 10
        this is the value at which the next trailing is done, in percentage
    trailing_mtm
        trailing mtm value, this is the value at which the next trailing is done, in absolute mtm
    trailing_step
        trailing step value, this is the value at which the next trailing is done, in absolute mtm
    start_trailing_at
        start trailing at this value, this is an absolute number
    returns
        trailing_stop, target.
        None if only last price is given
    Note
    ----
    1) provide either trailing_percent or trailing_mtm, if both are given, trailing_percent takes precedence
    """

    def all_none() -> bool:
        return (
            trailing_stop is None
            and target is None
            and trailing_percent is None
            and trailing_mtm is None
            and start_trailing_at is None
        )

    def trailing_none() -> bool:
        return (
            trailing_percent is None
            and trailing_mtm is None
            and start_trailing_at is None
        )

    if all_none():
        return trailing_values()
    if target and not trailing_stop and trailing_none():
        return trailing_values(target=target)
    if not target and trailing_stop and trailing_none():
        return trailing_values(stop=trailing_stop)
    if target and trailing_stop and trailing_none():
        return trailing_values(target=target, stop=trailing_stop)


class Trailing(BaseModel):
    """
    start_time
        starting time to trail
        this takes precendence over others and trailing is
        only started after this
    end_time
        end time for trailing
        trailing is not done after this
    target
        target value to exit
    trailing_stop
        the initial trailing stop value
    start_trailing_at
        start trailing at this value, this is an absolute number
    trailing_step
        trailing step value, this is the value at which the next trailing is done, in absolute mtm
    trailing_percent
        trailing percent from mtm, this is the value at which the next trailing is done, in percentage
    trailing_mtm
        trailing mtm value, this is the value at which the next trailing is done, in absolute mtm
    order
        the `CompoundOrder` containing all the orders
    Note
    ----
    1) start and end time takes precendence over all other arguments.
    2) provide either trailing_percent or trailing_mtm, if both are given, trailing_percent takes precedence
    """

    start_time: pendulum.DateTime
    end_time: pendulum.DateTime
    target: Optional[float] = None
    trailing_stop: Optional[float] = None
    start_trailing_at: Optional[float] = None
    trailing_step: Optional[float] = None
    trailing_percent: Optional[float] = None
    trailing_mtm: Optional[float] = None
    cycle: int = 0
    done: bool = False
    broker: Optional[Any] = None
    connection: Optional[Database] = None
    order: Optional[CompoundOrder] = None
    ltps: dict[str, float] = Field(default_factory=dict)
    _can_start_mtm_trailing: bool = False
    _next_trail: Optional[float] = None
    _previous_trail: Optional[float] = None

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        if self.order is None:
            self.order = CompoundOrder(broker=self.broker, connection=self.connection)

    @property
    def can_start_mtm_trailing(self) -> bool:
        return self._can_start_mtm_trailing

    @property
    def next_trail(self) -> Optional[float]:
        return self._next_trail

    @property
    def previous_trail(self) -> Optional[float]:
        return self._previous_trail

    @property
    def mtm(self) -> float:
        return self.order.total_mtm

    @property
    def can_trail(self) -> bool:
        time_trail = self.start_time <= pendulum.now(tz="local") <= self.end_time
        if self.start_trailing_at:
            if not self._can_start_mtm_trailing:
                self._can_start_mtm_trailing = self.mtm >= self.start_trailing_at
            return time_trail and self.can_start_mtm_trailing
        else:
            return time_trail

    def add(self, order: Order) -> None:
        """
        Add an order to the existing compound order
        """
        self.order.add(order)

    def trailing(self) -> TrailingResult:
        """
        return the trailing result
        """
        pass

    def run(self, data: dict[str, float]) -> None:
        """
        run the trailing logic with ltp data
        data
            ltp data as dictionary
        """
        self.ltp.update(data)
