"""
This module contains all the models for running the simulation
All the models start with **V** to indicate virtual models
"""

from pydantic import BaseModel
from typing import Optional, Union
import pendulum
import omspy.utils as utils


class VTrade(BaseModel):
    trade_id: str
    order_id: str
    symbol: str
    quantity: int
    price: float
    side: str
    timestamp: Optional[pendulum.DateTime]


class VOrder(BaseModel):
    order_id: str
    symbol: str
    quantity: Union[int, float]
    side: str
    price: Optional[float]
    average_price: Optional[float]
    trigger_price: Optional[float]
    timestamp: Optional[pendulum.DateTime]
    exchange_order_id: Optional[str]
    exchange_timestamp: Optional[pendulum.DateTime]
    status_message: Optional[str]
    filled_quantity: Union[int, float] = 0
    pending_quantity: Union[int, float] = 0
    canceled_quantity: Union[int, float] = 0

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


class VPosition(BaseModel):
    symbol: str
    buy_quantity: Union[int, float] = 0
    sell_quantity: Union[int, float] = 0
    buy_value: float = 0
    sell_value: float = 0
