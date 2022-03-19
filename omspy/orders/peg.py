from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
from omspy.base import Broker
from omspy.order import Order, CompoundOrder
from copy import deepcopy
import pendulum


class BasicPeg(CompoundOrder):
    symbol: str
    side: str
    quantity: int
    timezone:str = 'UTC'

    def __init__(self, **data) -> None:
        super().__init__(**data)
        pop_attribs = ['symbol', 'side', 'quantity',
                'timezone', 'order_type', 'connection']
        for attrib in pop_attribs:
            if attrib in data:
                data.pop(attrib)
        order = Order(
            symbol=self.symbol,
            quantity=self.quantity,
            side=self.side,
            timezone=self.timezone,
            order_type="LIMIT",
            **data
        )
        self.add(order)
        self.ltp[self.symbol] = 0


class PegMarket(BasicPeg):
    duration: int = 60
    peg_every: int = 10
    convert_to_market_after_expiry: bool = False
    _next_peg: Optional[pendulum.DateTime]
    _num_pegs: int = 0
    _max_pegs: int = 0
    _expire_at: Optional[pendulum.DateTime]

    def __init__(self, **data) -> None:
        super().__init__(**data)
        self._max_pegs = int(self.duration / self.peg_every)
        self._num_pegs = 0
        self._expire_at = pendulum.now(tz=self.timezone).add(seconds=self.duration)
        self._next_peg = pendulum.now(tz=self.timezone).add(seconds=self.peg_every)

    def execute(self):
        self.orders[0].price = self.ref_price
        self.orders[0].execute(broker=self.broker, **self.order_args)

    @property
    def next_peg(self):
        return self._next_peg

    @property
    def num_pegs(self):
        return self._num_pegs

    @property
    def ref_price(self):
        return self.ltp.get(self.symbol)

    def run(self):
        order = self.orders[0]
        now = pendulum.now(self.timezone)
        if order.is_pending:
            if now > self.next_peg:
                self._next_peg = now.add(seconds=self.peg_every)
                order.modify(broker=self.broker, price=self.ref_price)
            if now > self._expire_at:
                if self.convert_to_market_after_expiry:
                    order.modify(broker=self.broker, order_type="MARKET")
                else:
                    order.cancel(self.broker)
