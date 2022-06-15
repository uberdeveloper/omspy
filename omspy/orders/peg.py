from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
from omspy.base import Broker
from omspy.order import Order, CompoundOrder
from omspy.models import OrderLock
import pendulum
from pydantic import BaseModel, ValidationError, validator
import logging


class BasicPeg(CompoundOrder):
    symbol: str
    side: str
    quantity: int
    timezone: str = "UTC"

    def __init__(self, **data) -> None:
        super().__init__(**data)
        pop_attribs = [
            "symbol",
            "side",
            "quantity",
            "timezone",
            "order_type",
            "connection",
        ]
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
    convert_to_market_after_expiry = True
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


class PegExisting(BaseModel):
    order: Order
    broker: Any
    timezone: Optional[str] = None
    duration: int = 60
    peg_every: int = 10
    done: bool = False
    lock: Optional[OrderLock] = None
    lock_duration: int = 2
    _next_peg: Optional[pendulum.DateTime] = None
    _num_pegs: int = 0
    _max_pegs: int = 0
    _expire_at: Optional[pendulum.DateTime]

    class Config:
        underscore_attrs_are_private = True

    def __init__(self, **data) -> None:
        super().__init__(**data)
        self._max_pegs = int(self.duration / self.peg_every)
        self._num_pegs = 0
        self._expire_at = pendulum.now(tz=self.timezone).add(seconds=self.duration)
        self._next_peg = pendulum.now(tz=self.timezone).add(seconds=self.peg_every)
        self.order.order_type = "LIMIT"
        if self.lock is None:
            self.lock = OrderLock()

    @validator("order")
    def order_should_be_pending(cls, v):
        """
        Only accept a pending order
        """
        if not (v.is_pending):
            raise ValueError
        else:
            return v

    @property
    def next_peg(self) -> pendulum.DateTime:
        return self._next_peg

    @property
    def num_pegs(self) -> int:
        return self._num_pegs

    def execute(self, **order_args):
        self.order.execute(broker=self.broker)

    def _mark_done(self) -> bool:
        """
        Mark whether the order is done
        """
        if self.order.is_complete:
            self.done = True
        elif not (self.order.is_pending):
            self.done = True
        return self.done

    def run(self, ltp: float):
        if self.done:
            logging.warning("Order already done")
            return

        order = self.order
        now = pendulum.now(self.timezone)
        if order.is_pending:
            if now > self._expire_at:
                if self.order.convert_to_market_after_expiry:
                    if self.lock.can_modify:
                        order.modify(broker=self.broker, order_type="MARKET")
                        self.lock.modify(self.lock_duration)
                else:
                    if self.lock.can_cancel:
                        order.cancel(self.broker)
                        self.lock.cancel(self.lock_duration)
            elif now > self.next_peg:
                self._next_peg = now.add(seconds=self.peg_every)
                if self.lock.can_modify:
                    order.modify(broker=self.broker, price=ltp)
                    self.lock.modify(self.lock_duration)
        self._mark_done()


class PegSequential(BaseModel):
    """
    Peg orders in sequence and peg only when the
    previous order is complete
    """

    orders: List[Order]
    broker: Any
    timezone: Optional[str] = None
    duration: int = 12
    peg_every: int = 4
    lock_duration: int = 2
    done: bool = False
    _order: Optional[PegExisting] = None
    _start_time: Optional[pendulum.DateTime] = None

    class Config:
        underscore_attrs_are_private = True

    def __init__(self, **data) -> None:
        super().__init__(**data)
        # Validate whether orders could be pegged
        for order in self.orders:
            peg = PegExisting(
                order=order,
                timezone=self.timezone,
                duration=self.duration,
                peg_every=self.peg_every,
                lock_duration=self.lock_duration,
            )
        self._start_time = pendulum.now(tz=self.timezone)

    @property
    def has_expired(self) -> bool:
        """
        Whether the entire sequential order has expired.
        A sequential order is considered expired when the
        current time is greater than the maximum possible
        time taken by all the orders together
        Note
        ----
        1) total_time = duration*number of orders
        """
        total_time = self.duration * len(self.orders)
        if pendulum.now(tz=self.timezone) > self._start_time.add(seconds=total_time):
            return True
        else:
            return False

    @property
    def order(self) -> Optional[PegExisting]:
        return self._order

    @property
    def completed(self) -> List[Order]:
        """
        returns the list of completed orders
        """
        return [order for order in self.orders if order.is_complete]

    @property
    def pending(self):
        """
        returns the list of pending orders
        """
        return [order for order in self.orders if order.is_pending]

    @property
    def all_complete(self):
        """
        Whether all orders are completed
        """
        return all([order.is_complete for order in self.orders])

    def get_current_order(self) -> Union[PegExisting, None]:
        """
        Get the current order to peg
        """
        for order in self.orders:
            if order.is_pending:
                return PegExisting(
                    order=order,
                    broker=self.broker,
                    timezone=self.timezone,
                    duration=self.duration,
                    peg_every=self.peg_every,
                    lock_duration=self.lock_duration,
                )
        return None

    def set_current_order(self) -> Union[PegExisting, None]:
        """
        Set the current order for pegging
        Note
        ----
        1) Set the current order only when a existing peg
        order is complete or there is no peg order
        """
        if self.order is None:
            self._order = self.get_current_order()
        elif self.order.order.is_complete:
            self._order = self.get_current_order()
        return self.order

    def execute_all(self):
        # Execute all pending orders
        for order in self.orders:
            order.execute(broker=self.broker)

    def cancel_all(self):
        # Cancel all pending orders
        for order in self.orders:
            order.cancel(broker=self.broker)

    def run(self, ltp: Dict[str, float]):
        self.set_current_order()
        peg = self.order
        # Run only when there is an order
        if peg:
            if not (peg.order.order_id):
                # Place the order if it has not been placed yet
                peg.execute()
            symbol = peg.order.symbol
            last_price = ltp.get(symbol, 0)
            peg.run(ltp=last_price)

    def _mark_done(self):
        pass
