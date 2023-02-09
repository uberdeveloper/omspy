"""
This module contains all the models for running the simulation
All the models start with **V** to indicate virtual models
"""

from pydantic import BaseModel
from typing import Optional, Union
import pendulum


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
    filled_quantity: Optional[Union[int, float]]
    pending_quantity: Optional[Union[int, float]]
    canceled_quantity: Optional[Union[int, float]]


class VPosition(BaseModel):
    symbol: str
    buy_quantity: Union[int, float] = 0
    sell_quantity: Union[int, float] = 0
    buy_value: float = 0
    sell_value: float = 0
