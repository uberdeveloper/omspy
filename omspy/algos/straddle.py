from pydantic import BaseModel, ValidationError, validator
from typing import List, Optional, Type
from omspy.base import Broker
from omspy.order import Order, CompoundOrder
from omspy.models import Timer
import pendulum
import sqlite_utils


class BaseStrategy(BaseModel):
    start_time: pendulum.DateTime
    end_time: pendulum.DateTime
    cycle: int = 0
    done: bool = False
    broker: Optional[Type[Broker]] = None
    connection: Optional[sqlite_utils.Database] = None
    timezone: Optional[str] = None
    _timer: Optional[Timer] = None

    class Config:
        arbitrary_types_allowed = True
        underscore_attrs_are_private = True

    def __init__(self, **data):
        super().__init__(**data)
        self._timer = Timer(
            start_time=self.start_time, end_time=self.end_time, timezone=self.timezone
        )

    @property
    def timer(self):
        return self._timer

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
