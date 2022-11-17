from datetime import timezone
from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
from omspy.base import Broker
from omspy.order import Order, CompoundOrder
from pydantic import PrivateAttr


class StopOrder(CompoundOrder):
    symbol: str
    side: str
    trigger_price: float
    price: float = 0.0
    quantity: int = 1
    disclosed_quantity: int = 0
    order_type: Optional[Tuple[str, str]] = None
    # TODO: Add order lock on modify

    def __init__(self, **data):
        super().__init__(**data)
        if self.order_type is None:
            self.order_type = ("LIMIT", "SL-M")
        side_map = {"buy": "sell", "sell": "buy"}
        base_order = Order(
            symbol=self.symbol,
            side=self.side,
            quantity=self.quantity,
            disclosed_quantity=self.disclosed_quantity,
            order_type=self.order_type[0],
            price=self.price,
            trigger_price=0,
        )

        cover_order = base_order.clone()
        cover_order.trigger_price = self.trigger_price
        cover_order.order_type = self.order_type[1]
        cover_order.side = side_map.get(cover_order.side)
        self.add(base_order)
        self.add(cover_order)


class StopLimitOrder(StopOrder):
    """
    Stop Loss Limit order
    stop_limit_price
        limit price for the stop order
    """

    stop_limit_price: float
    order_type: Tuple[str, str] = ("LIMIT", "SL")

    def __init__(self, order_type, **data):
        super().__init__(**data)
        self.orders[0].order_type = self.order_type[0]
        self.orders[-1].order_type = self.order_type[1]
        self.orders[-1].price = self.stop_limit_price


class TrailingStopOrder(StopOrder):
    """
    Trailing stop order
    trail_by
        trail_by in price
    """

    trail_by: float
    _next_trail: Optional[float] = PrivateAttr()
    _stop_loss: float = PrivateAttr()

    @property
    def sign(self) -> int:
        return 1 if self.side == "buy" else -1

    def __init__(self, **data):
        super().__init__(**data)
        self._stop_loss = self.trigger_price
        self._update_next_trail()

    def _update_next_trail(self):
        """
        Update trailing stop loss
        """
        price = self.orders[0].average_price if self.price == 0 else self.price
        if self.price > 0:
            self._next_trail = price + self.trail_by * self.sign * 1
        else:
            self._next_trail = 0

    @property
    def next_trail(self) -> float:
        return self._next_trail

    def run(self, ltp: float):
        """
        Update trailing stop
        """
        if self.next_trail == 0:
            self._update_next_trail()
        if self.next_trail > 0:
            if self.side == "buy":
                if ltp > self.next_trail:
                    # TODO: Trail to adjust to the nearest trail in case of jump in ltp
                    self._stop_loss += self.trail_by
                    self._next_trail += self.trail_by
                    self.orders[-1].modify(
                        broker=self.broker, trigger_price=self._stop_loss
                    )
            elif self.side == "sell":
                if ltp < self.next_trail:
                    self._stop_loss -= self.trail_by
                    self._next_trail -= self.next_trail
                    self.orders[-1].modify(
                        broker=self.broker, trigger_price=self._stop_loss
                    )


class TargetOrder(StopOrder):
    """
    Exit an order when the target price is hit
    target
        target price to exit order
    Note
    -----
    1) The existing stop loss order is converted into a MARKET order when the target price is hit
    """

    target: float
    order_type: Tuple[str, str] = ("LIMIT", "SL-M")

    def __init__(self, **data):
        super().__init__(**data)

    def run(self, ltp: float):
        """
        Update and exit if target is hit
        """
        price = self.price if self.price > 0 else self.orders[0].average_price
        if price > 0:
            if self.side == "buy":
                if ltp >= self.target:
                    self.orders[-1].modify(broker=self.broker, order_type="MARKET")
            elif self.side == "sell":
                if ltp <= self.target:
                    self.orders[-1].modify(broker=self.broker, order_type="MARKET")
