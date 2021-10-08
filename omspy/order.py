from dataclasses import dataclass, field
from datetime import timezone
from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
from fastbt.Meta import Broker
import uuid
import pendulum
from collections import Counter, defaultdict


def get_option(spot: float, num: int = 0, step: float = 100.0) -> float:
    """
    Get the option price given number of strikes
    spot
        spot price of the instrument
    num
        number of strikes farther
    step
        step size of the option
    Note
    ----
    1. By default, the ATM option is fetched
    """
    v = round(spot / step)
    return v * (step + num)

@dataclass
class Order:
    symbol: str
    side: str
    quantity: int = 1
    internal_id: Optional[str] = None
    parent_id: Optional[str] = None
    timestamp: Optional[pendulum.DateTime] = None
    order_type: str = "MARKET"
    broker_timestamp: Optional[pendulum.DateTime] = None
    exchange_timestamp: Optional[pendulum.DateTime] = None
    order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    price: Optional[float] = None
    trigger_price: float = 0.0
    average_price: float = 0.0
    pending_quantity: Optional[int] = None
    filled_quantity: int = 0
    cancelled_quantity: int = 0
    disclosed_quantity: int = 0
    validity: str = "DAY"
    status: Optional[str] = None
    expires_in: int = 0
    timezone: str = "UTC"
    client_id: Optional[str] = None
    convert_to_market_after_expiry: bool = False
    cancel_after_expiry: bool = True
    retries: int = 0
    exchange: Optional[str] = None
    tag: Optional[str] = None

    def __post_init__(self) -> None:
        self.internal_id = uuid.uuid4().hex
        tz = self.timezone
        self.timestamp = pendulum.now(tz=tz)
        self.pending_quantity = self.quantity
        self._attrs: List[str] = [
            "exchange_timestamp",
            "exchange_order_id",
            "status",
            "filled_quantity",
            "pending_quantity",
            "disclosed_quantity",
            "average_price",
        ]
        if self.expires_in == 0:
            self.expires_in = (
                pendulum.today(tz=tz).end_of("day") - pendulum.now(tz=tz)
            ).seconds
        else:
            self.expires_in = abs(self.expires_in)

    @property
    def is_complete(self) -> bool:
        if self.quantity == self.filled_quantity:
            return True
        elif self.status == "COMPLETE":
            return True
        elif (self.filled_quantity + self.cancelled_quantity) == self.quantity:
            return True
        else:
            return False

    @property
    def is_pending(self) -> bool:
        quantity = self.filled_quantity + self.cancelled_quantity
        if self.status == "COMPLETE":
            return False
        elif quantity < self.quantity:
            return True
        else:
            return False

    @property
    def time_to_expiry(self) -> int:
        now = pendulum.now(tz=self.timezone)
        ts = self.timestamp
        return max(0, self.expires_in - (now - ts).seconds)

    @property
    def time_after_expiry(self) -> int:
        now = pendulum.now(tz=self.timezone)
        ts = self.timestamp
        return max(0, (now - ts).seconds - self.expires_in)

    @property
    def has_expired(self) -> bool:
        return True if self.time_to_expiry == 0 else False

    @property
    def has_parent(self) -> bool:
        return True if self.parent_id else False

    def update(self, data: Dict[str, Any]) -> bool:
        """
        Update order based on information received from broker
        data
            data to update as dictionary
        returns True if update is done
        Note
        ----
        1) Information is updated only for those keys specified in attrs
        2) Information is updated only when the order is not completed
        """
        if not (self.is_complete):
            for att in self._attrs:
                val = data.get(att)
                if val:
                    setattr(self, att, val)
            return True
        else:
            return False

    def execute(self, broker: Broker, **kwargs) -> Optional[str]:
        """
        Execute an order on a broker, place a new order
        kwargs
            Additional arguments to the order
        Note
        ----
        Only new arguments added to the order in keyword arguments
        """
        # Do not place a new order if this order is complete or has order_id
        if not (self.is_complete) and not (self.order_id):
            order_args = {
                "symbol": self.symbol.upper(),
                "side": self.side.upper(),
                "order_type": self.order_type.upper(),
                "quantity": self.quantity,
                "price": self.price,
                "trigger_price": self.trigger_price,
                "disclosed_quantity": self.disclosed_quantity,
            }
            dct = {k: v for k, v in kwargs.items() if k not in order_args.keys()}
            order_args.update(dct)
            order_id = broker.order_place(**order_args)
            self.order_id = order_id
            return order_id
        else:
            return self.order_id

    def modify(self, broker: Broker, **kwargs):
        """
        Modify an existing order
        """
        order_args = {
            "order_id": self.order_id,
            "quantity": self.quantity,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "order_type": self.order_type.upper(),
            "disclosed_quantity": self.disclosed_quantity,
        }
        dct = {k: v for k, v in kwargs.items() if k not in order_args.keys()}
        order_args.update(dct)
        broker.order_modify(**order_args)

    def cancel(self, broker: Broker):
        """
        Cancel an existing order
        """
        broker.order_cancel(order_id=self.order_id)

@dataclass
class CompoundOrder:
    broker: Type[Broker]
    internal_id: Optional[str] = None

    def __post_init__(self) -> None:
        self.internal_id = uuid.uuid4().hex
        self._ltp: defaultdict = defaultdict()
        self._orders: List[Order] = []

    @property
    def orders(self) -> List[Order]:
        return self._orders

    @property
    def count(self) -> int:
        """
        return the number of orders
        """
        return len(self.orders)

    @property
    def ltp(self) -> defaultdict:
        return self._ltp

    @property
    def positions(self) -> Counter:
        """
        return the positions as a dictionary
        """
        c: Counter = Counter()
        for order in self.orders:
            symbol = order.symbol
            qty = order.filled_quantity
            side = str(order.side).lower()
            sign = -1 if side == "sell" else 1
            qty = qty * sign
            c.update({symbol: qty})
        return c

    def add_order(self, **kwargs) -> Optional[str]:
        kwargs["parent_id"] = self.internal_id
        order = Order(**kwargs)
        self._orders.append(order)
        return order.internal_id

    def _average_price(self, side: str = "buy") -> Dict[str, float]:
        """
        Get the average price for all the instruments
        side
            side to calculate average price - buy or sel
        """
        side = str(side).lower()
        value_counter: Counter = Counter()
        quantity_counter: Counter = Counter()
        for order in self.orders:
            order_side = str(order.side).lower()
            if side == order_side:
                symbol = order.symbol
                price = order.average_price
                quantity = order.filled_quantity
                value = price * quantity
                value_counter.update({symbol: value})
                quantity_counter.update({symbol: quantity})
        dct: defaultdict = defaultdict()
        for v in value_counter:
            numerator = value_counter.get(v)
            denominator = quantity_counter.get(v)
            if numerator and denominator:
                dct[v] = numerator / denominator
        return dct

    @property
    def average_buy_price(self) -> Dict[str, float]:
        return self._average_price(side="buy")

    @property
    def average_sell_price(self) -> Dict[str, float]:
        return self._average_price(side="sell")

    def update_orders(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        Update all orders
        data
            data as dictionary with key as broker order_id
        returns a dictionary with order_id and update status as boolean
        """
        dct: Dict[str, bool] = {}
        for order in self.orders:
            order_id = str(order.order_id)
            status = order.status
            if (order_id in data) and (status != "COMPLETE"):
                d = data.get(order_id)
                if d:
                    order.update(d)
                    dct[order_id] = True
                else:
                    dct[order_id] = False
            else:
                dct[order_id] = False
        return dct

    def _total_quantity(self) -> Dict[str, Counter]:
        """
        Get the total buy and sell quantity by symbol
        """
        buy_counter: Counter = Counter()
        sell_counter: Counter = Counter()
        for order in self.orders:
            side = order.side.lower()
            symbol = order.symbol
            quantity = abs(order.filled_quantity)
            if side == "buy":
                buy_counter.update({symbol: quantity})
            elif side == "sell":
                sell_counter.update({symbol: quantity})
        return {"buy": buy_counter, "sell": sell_counter}

    @property
    def buy_quantity(self) -> Counter:
        return self._total_quantity()["buy"]

    @property
    def sell_quantity(self) -> Counter:
        return self._total_quantity()["sell"]

    def update_ltp(self, last_price: Dict[str, float]):
        """
        Update ltp for the given symbols
        last_price
            dictionary with symbol as key and last price as value
        returns the ltp for all the symbols
        Note
        ----
        1. Last price is updated for all given symbols irrespective of
        orders placed
        """
        for symbol, ltp in last_price.items():
            self._ltp[symbol] = ltp
        return self.ltp

    @property
    def net_value(self) -> Counter:
        """
        Return the net value by symbol
        """
        c: Counter = Counter()
        for order in self.orders:
            symbol = order.symbol
            side = str(order.side).lower()
            sign = -1 if side == "sell" else 1
            value = order.filled_quantity * order.average_price * sign
            c.update({symbol: value})
        return c

    @property
    def mtm(self) -> Counter:
        c: Counter = Counter()
        net_value = self.net_value
        positions = self.positions
        ltp = self.ltp
        for symbol, value in net_value.items():
            c.update({symbol: -value})
        for symbol, quantity in positions.items():
            v = quantity * ltp.get(symbol, 0)
            c.update({symbol: v})
        return c

    @property
    def total_mtm(self) -> float:
        return sum(self.mtm.values())

    def execute_all(self):
        for order in self.orders:
            order.execute(broker=self.broker)

    def check_flags(self):
        """
        Check for flags on each order and take suitable action
        """
        for order in self.orders:
            if (order.is_pending) and (order.has_expired):
                if order.convert_to_market_after_expiry:
                    order.order_type = "MARKET"
                    order.modify(self.broker)
                elif order.cancel_after_expiry:
                    order.cancel(broker=self.broker)

    @property
    def completed_orders(self) -> List[Order]:
        return [order for order in self.orders if order.is_complete]

    @property
    def pending_orders(self) -> List[Order]:
        return [order for order in self.orders if order.is_pending]


    def __init__(
        self,
        symbol: str,
        side: str,
        trigger_price: float,
        price: float = 0.0,
        quantity: int = 1,
        order_type="MARKET",
        disclosed_quantity: int = 0,
        order_args: Optional[Dict] = None,
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

class OptionStrategy:
    """
    Option Strategy is a list of compound orders
    """

    def __init__(self, broker: Type[Broker], profit=1e100, loss=-1e100) -> None:
        self._orders: List[CompoundOrder] = []
        self._broker: Type[Broker] = broker
        self._ltp: defaultdict = defaultdict()
        self.profit: float = profit
        self.loss: float = loss

    @property
    def broker(self) -> Type[Broker]:
        return self._broker

    @property
    def orders(self) -> List[CompoundOrder]:
        return self._orders

    def add_order(self, order: CompoundOrder) -> None:
        """
        Add a compound order
        broker is overriden
        """
        order.broker = self.broker
        self._orders.append(order)

    @property
    def all_orders(self) -> List[Order]:
        """
        Get the list of all orders
        """
        orders = []
        for order in self.orders:
            orders.extend(order.orders)
        return orders

    def update_ltp(self, last_price: Dict[str, float]) -> List[Any]:
        """
        Update ltp for the given symbols
        last_price
            dictionary with symbol as key and last price as value
        """
        return self._call("update_ltp", last_price=last_price)

    def _call(self, attribute: str, **kwargs) -> List[Any]:
        """
        Call the given method or property on each of the compound orders
        attribute
            property or method
        kwargs
            keyword arguments to be called in case of a method
        returns a list of the return values
        Note
        -----
        1) An attribtute is considered to be a method if callable returns True
        """
        responses = []
        for order in self.orders:
            attr = getattr(order, attribute, None)
            if callable(attr):
                responses.append(attr(**kwargs))
            else:
                responses.append(attr)
        return responses

    def update_orders(self, data: Dict[str, Dict[str, Any]]) -> List[Any]:
        """
        Update all orders
        data
            data as dictionary with key as broker order_id
        returns a dictionary with order_id and update status as boolean
        for all compound orders
        """
        return self._call("update_orders", data=data)

    def execute_all(self) -> List[Any]:
        """
        Execute all orders in all compound orders
        """
        return self._call("execute_all")

    @property
    def total_mtm(self) -> float:
        """
        Returns the total mtm for this strategy
        """
        mtm = self._call("total_mtm")
        return sum([x for x in mtm if x is not None])

    @property
    def positions(self) -> Counter:
        """
        Return the combined positions for this strategy
        """
        c: Counter = Counter()
        positions = self._call("positions")
        for position in positions:
            c.update(position)
        return c

    @property
    def is_profit_hit(self) -> bool:
        return True if self.total_mtm > self.profit else False

    @property
    def is_loss_hit(self) -> bool:
        return True if self.total_mtm < self.loss else False

    @property
    def can_exit_strategy(self) -> bool:
        """
        Check whether we can exit from the strategy
        We can exit from the strategy if either of the following
        conditions is met
        1) Profit is hit
        2) Loss is hit
        """
        if self.is_profit_hit:
            return True
        elif self.is_loss_hit:
            return True
        else:
            return False

    """
    Trailing stop order
    """
    def __init__(self, trail_by:Tuple[float, float],**kwargs):
        self.trail_big:float = trail_by[0]
        self.trail_small:float = trail_by[-1]
        super(TrailingStopOrder, self).__init__(**kwargs)
        self._maxmtm:float = 0
        self._stop:float = kwargs.get('trigger_price', 0)
        self.initial_stop = self._stop
        self.symbol:str = kwargs.get('symbol')
        self.quantity:int = kwargs.get('quantity',1)

    @property
    def stop(self):
        return self._stop

    @property
    def maxmtm(self):
        return self._maxmtm
    
    def _update_maxmtm(self):
        self._maxmtm = max(self.total_mtm, self._maxmtm)

    def _update_stop(self):
        mtm_per_unit = self.maxmtm/self.quantity
        multiplier = self.trail_small/self.trail_big
        self._stop = self.initial_stop + (mtm_per_unit*multiplier)
        
    def watch(self):
        self._update_maxmtm()
        self._update_stop()
        ltp = self.ltp.get(self.symbol)
        if ltp:
            #TODO: Implement for sell also
            if ltp < self.stop:
                order = self.orders[-1]
                order.order_type = "MARKET"
                order.modify(broker=self.broker)



