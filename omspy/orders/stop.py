from datetime import timezone
from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
from omspy.base import Broker
from omspy.order import Order, CompoundOrder


class StopOrder(CompoundOrder):
    def __init__(
        self,
        symbol: str,
        side: str,
        trigger_price: float,
        price: float = 0.0,
        quantity: int = 1,
        order_type="MARKET",
        disclosed_quantity: int = 0,
        **kwargs,
    ):
        super(StopOrder, self).__init__(**kwargs)
        side2 = "sell" if side.lower() == "buy" else "buy"
        self.add_order(
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            order_type=order_type,
            disclosed_quantity=disclosed_quantity,
        )
        self.add_order(
            symbol=symbol,
            side=side2,
            price=0,
            trigger_price=trigger_price,
            quantity=quantity,
            order_type="SL-M",
            disclosed_quantity=disclosed_quantity,
        )


class StopLimitOrder(CompoundOrder):
    def __init__(
        self,
        symbol: str,
        side: str,
        trigger_price: float,
        price: float = 0.0,
        stop_limit_price: float = 0.0,
        quantity: int = 1,
        order_type="MARKET",
        disclosed_quantity: int = 0,
        **kwargs,
    ):
        super(StopLimitOrder, self).__init__(**kwargs)
        side2 = "sell" if side.lower() == "buy" else "buy"
        if stop_limit_price == 0:
            stop_limit_price = trigger_price
        self.add_order(
            symbol=symbol,
            side=side,
            price=price,
            quantity=quantity,
            order_type=order_type,
            disclosed_quantity=disclosed_quantity,
        )
        self.add_order(
            symbol=symbol,
            side=side2,
            price=stop_limit_price,
            trigger_price=trigger_price,
            quantity=quantity,
            order_type="SL",
            disclosed_quantity=disclosed_quantity,
        )


class BracketOrder(StopOrder):
    def __init__(self, target: float, **kwargs):
        super(BracketOrder, self).__init__(**kwargs)
        self._target = target

    @property
    def target(self) -> float:
        return self._target

    @property
    def is_target_hit(self) -> bool:
        """
        Check whether the given target is hit
        """
        for k, v in self.ltp.items():
            # We assume a single symbol only so breaking
            # TO DO: A better way is appreciated
            ltp = v
            break
        return True if ltp > self.target else False

    def do_target(self) -> None:
        """
        Execute target order if target is hit
        Note
        -----
        This checks
         1. whether the target is hit
         2. if target is hit, modify the existing stop and exit the order
        """
        if self.is_target_hit:
            order = self.orders[-1]
            order.order_type = "MARKET"
            order.modify(broker=self.broker)


class TrailingStopOrder(StopLimitOrder):
    """
    Trailing stop order
    """

    def __init__(self, trail_by: Tuple[float, float], **kwargs):
        super(TrailingStopOrder, self).__init__(**kwargs)
        self.trail_big: float = trail_by[0]
        self.trail_small: float = trail_by[-1]
        self._maxmtm: float = 0
        self._stop: float = kwargs.get("trigger_price", 0)
        self.initial_stop = self._stop
        self.symbol: str = kwargs.get("symbol")
        self.quantity: int = kwargs.get("quantity", 1)

    @property
    def stop(self):
        return self._stop

    @property
    def maxmtm(self):
        return self._maxmtm

    def _update_maxmtm(self):
        self._maxmtm = max(self.total_mtm, self._maxmtm)

    def _update_stop(self):
        mtm_per_unit = self.maxmtm / self.quantity
        multiplier = self.trail_small / self.trail_big
        self._stop = self.initial_stop + (mtm_per_unit * multiplier)

    def watch(self):
        self._update_maxmtm()
        self._update_stop()
        ltp = self.ltp.get(self.symbol)
        if ltp:
            # TODO: Implement for sell also
            if ltp < self.stop:
                order = self.orders[-1]
                order.order_type = "MARKET"
                order.modify(broker=self.broker)
