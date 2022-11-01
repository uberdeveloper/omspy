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
    timezone: Optional[
        str
    ] = "local"  # "local" is same as None - when used with Timer (make intention explicit)
    _timer: Optional[
        Timer
    ] = None  # BaseStrategy __init__ uses timezone above in __init__ call of Timer
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

    def update_orders(self, orders: Optional[Dict[str, Dict]] = None):
        """
        Update existing orders
        """
        if orders is None:
            orders = self.broker.orders
        if hasattr(self, "_order"):
            for order in self._order.orders:
                o = orders.get(order.id)
                if o:
                    order.update(o)


class ShortStraddle(BaseStrategy):
    symbols: Tuple[str, str]
    limit_price: Optional[Tuple[float, float]] = (0.0, 0.0)
    trigger_price: Optional[Tuple[float, float]] = (0.0, 0.0)
    stop_price: Optional[Tuple[float, float]] = (0.0, 0.0)
    quantity: int = 1
    exclude_stop: bool = False
    ltp: Dict[str, float] = {}
    _order: Optional[CompoundOrder] = None
    _order_map: Optional[Dict[str, Order]] = None

    def __init__(self, **data):
        super().__init__(**data)
        self._order = CompoundOrder(
            broker=self.broker, connection=self.connection, timezone=self.timezone
        )
        self._order_map = dict(entry1=None, exit1=None, entry2=None, exit2=None)
        for symbol in self.symbols:
            self.ltp[symbol] = 0

    @property
    def order(self) -> CompoundOrder:
        return self._order

    def get_order(self, name: str) -> Union[Order, None]:
        """
        Get order by name/key
        Note
        ----
        1) Orders are named entry1, exit1, entry2, exit2 for easy reference
        """
        return self._order_map.get(name)

    def create_order(self):
        if len(self._order.orders) > 0:
            return
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
        self._order_map["entry1"] = order1
        self._order_map["exit1"] = order1stop
        self._order_map["entry2"] = order2
        self._order_map["exit2"] = order2stop
        return self.order

    @staticmethod
    def _check_orders_complete(one: Order, two: Order) -> bool:
        """
        returns whether the first leg of the order is complete
        Note
        ----
        1) returns True if both orders are complete or rejected or canceled
        2) returns True even if one order is rejected and other order is canceled
        """
        statuses = ("REJECTED", "CANCELED", "CANCELLED")
        if one.is_complete and two.is_complete:
            return True
        elif one.status in statuses and two.status in statuses:
            return True
        else:
            return False

    @property
    def is_first_leg_complete(self) -> bool:
        """
        returns whether the first leg of the order is complete
        Note
        ----
        1) returns True if both orders are complete or rejected or canceled
        2) returns True even if one order is rejected and other order is canceled
        """
        one = self.get_order("entry1")
        two = self.get_order("exit1")
        if one is None or two is None:
            return False
        else:
            return self._check_orders_complete(one, two)

    @property
    def is_second_leg_complete(self) -> bool:
        """
        returns whether the first leg of the order is complete
        Note
        ----
        1) returns True if both orders are complete or rejected or canceled
        2) returns True even if one order is rejected and other order is canceled
        """
        one = self.get_order("entry2")
        two = self.get_order("exit2")
        if one is None or two is None:
            return False
        else:
            return self._check_orders_complete(one, two)

    def _check_sell_without_buy(self, one: Order, two: Order) -> bool:
        """
        one
            the sell order
        two
            the corresponding buy order
        returns True if a sell order is without a buy order
        Note
        ----
        If this returns True, then it is not valid
        """
        status_one = one.status
        status_two = two.status
        statuses = ("REJECTED", "CANCELED", "CANCELLED")
        if one.is_complete and status_two in statuses:
            return True
        elif one.is_pending and status_two in statuses:
            return True
        else:
            return False

    def _check_buy_without_sell(self, one: Order, two: Order) -> bool:
        """
        one
            the sell order
        two
            the corresponding buy order
        returns True if a buy order is without a sell order
        Note
        ----
        If this returns True, then it is not valid
        """
        # Just swapping the arguments
        return self._check_sell_without_buy(two, one)

    def update_ltp(self, ltp: Dict[str, float]):
        """
        Update ltp for the given symbols
        """
        num = len(self.symbols)
        count = 0
        for symbol, last_price in ltp.items():
            if symbol in self.ltp:
                self.ltp[symbol] = last_price
                count += 1
            if count >= num:
                break
        return self.ltp

    def _make_sequential_orders(self):
        """
        Make sequential peg orders
        """
        if len(self._pegs) == 0 and len(self.order.orders) == 4:
            seq1 = PegSequential(
                broker=self.broker,
                timezone=self.timezone,
                start_time=self.start_time,
                orders=[self.get_order("entry1"), self.get_order("exit1")],
            )
            seq2 = PegSequential(
                broker=self.broker,
                timezone=self.timezone,
                start_time=self.start_time,
                orders=[self.get_order("entry2"), self.get_order("exit2")],
            )
            self._pegs.append(seq1)
            self._pegs.append(seq2)
