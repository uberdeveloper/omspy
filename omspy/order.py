from pydantic import BaseModel, validator, ValidationError, Field, PrivateAttr
from pydantic.dataclasses import dataclass
from datetime import timezone
from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
import uuid
import pendulum
import sqlite3
import logging
from collections import Counter, defaultdict
from omspy.base import Broker
from copy import deepcopy


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


def create_db(dbname: str = ":memory:") -> Union[sqlite3.Connection, None]:
    """
    Create a sqlite3 database for the orders and return the connection
    dbname
        name of the database
        default in-memory database
    """
    try:
        con = sqlite3.connect(dbname)
        with con:
            con.execute(
                """create table orders
                           (symbol text, side text, quantity integer,
                           id text primary key, parent_id text, timestamp text,
                           order_type text, broker_timestamp text,
                           exchange_timestamp text, order_id text,
                           exchange_order_id text, price real,
                           trigger_price real, average_price real,
                           pending_quantity integer, filled_quantity integer,
                           cancelled_quantity integer, disclosed_quantity integer,
                           validity text, status text,
                           expires_in integer, timezone text,
                           client_id text, convert_to_market_after_expiry text,
                           cancel_after_expiry text, retries integer,
                           exchange text, tag string)"""
            )
            return con
    except Exception as e:
        print("error is", e)
        return None


@dataclass
class Order:
    symbol: str
    side: str
    quantity: int = 1
    id: Optional[str] = None
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
    connection: Optional[Any] = None

    def __post_init__(self, **data) -> None:
        if not (self.id):
            self.id = uuid.uuid4().hex
        tz = self.timezone
        self.timestamp = pendulum.now(tz=tz)
        self.pending_quantity = self.quantity
        if self.expires_in == 0:
            self.expires_in = (
                pendulum.today(tz=tz).end_of("day") - pendulum.now(tz=tz)
            ).seconds
        else:
            self.expires_in = abs(self.expires_in)

    @property
    def _attrs(self):
        return (
            "exchange_timestamp",
            "exchange_order_id",
            "status",
            "filled_quantity",
            "pending_quantity",
            "disclosed_quantity",
            "average_price",
        )

    @validator("quantity", always=True)
    def quantity_not_negative(cls, v):
        if v < 0:
            raise ValueError("quantity must be positive")
        return v

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

    def update(self, data: Dict[str, Any], save: bool = True) -> bool:
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
            if self.connection and save:
                self.save_to_db()
            return True
        else:
            return False

    def execute(self, broker: Type[Broker], **kwargs) -> Optional[str]:
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

    def save_to_db(self) -> bool:
        """
        save or update the order to db
        """
        if self.connection:
            sql = """insert or replace into orders
            values (:symbol, :side, :quantity, :id,
            :parent_id, :timestamp, :order_type,
            :broker_timestamp, :exchange_timestamp, :order_id,
            :exchange_order_id, :price, :trigger_price,
            :average_price,:pending_quantity,:filled_quantity,
            :cancelled_quantity,:disclosed_quantity,:validity,
            :status,:expires_in,:timezone,:client_id,
            :convert_to_market_after_expiry,
            :cancel_after_expiry, :retries, :exchange, :tag)
            """
            values = dict(
                symbol=self.symbol,
                side=self.side,
                quantity=self.quantity,
                id=self.id,
                parent_id=self.parent_id,
                timestamp=str(self.timestamp),
                order_type=self.order_type,
                broker_timestamp=str(self.broker_timestamp),
                exchange_timestamp=str(self.exchange_timestamp),
                order_id=self.order_id,
                exchange_order_id=self.exchange_order_id,
                price=self.price,
                trigger_price=self.trigger_price,
                average_price=self.average_price,
                pending_quantity=self.pending_quantity,
                filled_quantity=self.filled_quantity,
                cancelled_quantity=self.cancelled_quantity,
                disclosed_quantity=self.disclosed_quantity,
                validity=self.validity,
                status=self.status,
                expires_in=self.expires_in,
                timezone=self.timezone,
                client_id=self.client_id,
                convert_to_market_after_expiry=self.convert_to_market_after_expiry,
                cancel_after_expiry=self.cancel_after_expiry,
                retries=self.retries,
                exchange=self.exchange,
                tag=self.tag,
            )
            with self.connection:
                self.connection.execute(sql, values)
                return True

        else:
            logging.info("No valid database connection")
            return False


@dataclass
class CompoundOrder:
    broker: Any
    id: Optional[str] = None
    ltp: defaultdict = Field(default_factory=defaultdict)
    orders: List[Order] = Field(default_factory=list)
    connection: Optional[Any] = None
    order_args: Optional[Dict] = None

    def __post_init__(self) -> None:
        if not (self.id):
            self.id = uuid.uuid4().hex
        if self.order_args is None:
            self.order_args = {}

    @property
    def count(self) -> int:
        """
        return the number of orders
        """
        return len(self.orders)

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
        kwargs["parent_id"] = self.id
        if not (kwargs.get("connection")):
            kwargs["connection"] = self.connection
        order = Order(**kwargs)
        order.save_to_db()
        self.orders.append(order)
        return order.id

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
        for order in self.pending_orders:
            order_id = str(order.order_id)
            status = order.status
            if order_id in data:
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
            self.ltp[symbol] = ltp
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

    def execute_all(self, **kwargs):
        for order in self.orders:
            order_args = deepcopy(self.order_args)
            order_args.update(kwargs)
            order.execute(broker=self.broker, **order_args)

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
