from pydantic import BaseModel, ValidationError, validator
from typing import List, Optional, Type, Tuple, Union, Dict
from omspy.base import Broker
from omspy.order import Order, CompoundOrder
from omspy.models import Timer
from omspy.orders.peg import PegExisting, PegSequential
import pendulum
import sqlite_utils
import logging


class BaseStrategy(BaseModel):
    start_time: pendulum.DateTime
    end_time: pendulum.DateTime
    cycle: int = 0
    done: bool = False
    broker: Optional[Type[Broker]] = None
    connection: Optional[sqlite_utils.Database] = None
    timezone: Optional[str] = None
    _timer: Optional[Timer] = None
    _pegs: List[Union[PegExisting, PegSequential]] = []

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


class ShortStraddle(BaseStrategy):
    symbols: Tuple[str, str]
    limit_price: Optional[Tuple[float, float]] = (0.0, 0.0)
    trigger_price: Optional[Tuple[float, float]] = (0.0, 0.0)
    stop_price: Optional[Tuple[float, float]] = (0.0, 0.0)
    quantity: int = 1
    exclude_stop: bool = False
    _order: Optional[CompoundOrder] = None
    _order_map: Optional[Dict[str, CompoundOrder]] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._order = CompoundOrder(
            broker=self.broker, connection=self.connection, timezone=self.timezone
        )
        self._order_map = dict(entry1=None, exit1=None, entry2=None, exit2=None)

    @property
    def order(self) -> CompoundOrder:
        return self._order

    def get_order(self, name: str):
        pass

    def create_order(self):
        com = self._order
        s1, s2 = self.symbols
        order1 = Order(symbol=s1, side="sell", quantity=self.quantity)
        order1.price = self.limit_price[0]
        order2 = order1.clone()
        order2.symbol = s2
        order2.price = self.limit_price[1]
        com.add(order1)
        com.add(order2)
        order1stop = order1.clone()
        order1stop.trigger_price = self.trigger_price[0]
        order1stop.price = self.stop_price[0]
        order1stop.order_type = "SL"
        order1stop.side = "buy"
        com.add(order1stop)
        order2stop = order2.clone()
        order2stop.trigger_price = self.trigger_price[1]
        order2stop.price = self.stop_price[1]
        order2stop.order_type = "SL"
        order2stop.side = "buy"
        com.add(order2stop)
        return self.order

    def check_sell_both_sides(self) -> bool:
        """
        Check whether the sell order is placed on both the
        sides and the orders are completed
        """
        orders = self.order.orders
        if orders[0].is_complete and orders[1].is_complete:
            return True
