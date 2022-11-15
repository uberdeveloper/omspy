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


class TrailingStopOrder(StopLimitOrder):
    """
    Trailing stop order
    trail_by
        trail_by in points
    """

    trail_by: float = 0.0
    _next_trail = PrivateAttr()

    def __init__(self):
        super().__init__(**data)
