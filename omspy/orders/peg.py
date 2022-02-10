from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
from omspy.base import Broker
from omspy.order import Order, CompoundOrder
import pendulum


class BasicPeg(CompoundOrder):
    symbol: str
    side: str
    quantity: int
    timezone: str = "UTC"

    def __init__(self, **data) -> None:
        super().__init__(**data)
        order = Order(
            symbol=self.symbol,
            quantity=self.quantity,
            side=self.side,
            order_type="LIMIT",
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

    @property
    def next_peg(self):
        return self._next_peg

    @property
    def num_pegs(self):
        return self._num_pegs
