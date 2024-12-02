import pendulum
from omspy.order import Order, CompoundOrder
from pydantic import BaseModel, PrivateAttr, Field
from sqlite_utils import Database
from typing import Optional, Any, NamedTuple
from collections import namedtuple

trailing_values = namedtuple("trailing", ["stop", "target"], defaults=[None, None])


def get_trailing_stop_and_target(
    last_price: float,
    max_mtm: float,
    min_mtm: float,
    target: Optional[float] = None,
    trailing_stop: Optional[float] = None,
    trailing_percent: Optional[float] = None,
    trailing_mtm: Optional[float] = None,
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
    ltp: dict[str, float] = Field(default_factory=dict)

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True

    def __init__(self, **data):
        super().__init__(**data)
        if self.order is None:
            self.order = CompoundOrder(broker=self.broker, connection=self.connection)
