import pendulum
from omspy.order import Order, CompoundOrder
from pydantic import BaseModel, PrivateAttr, Field
from sqlite_utils import Database
from typing import Optional, Any


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
