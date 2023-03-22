from pydantic import BaseModel, validator, Field, PrivateAttr, Json
from datetime import timezone
from typing import (
    Optional,
    Dict,
    List,
    Type,
    Any,
    Union,
    Tuple,
    Callable,
    Set,
    Hashable,
)
import uuid
import pendulum
import sqlite3
import logging
from collections import Counter, defaultdict
from collections.abc import Iterable
from omspy.base import *
from copy import deepcopy
from sqlite_utils import Database
from omspy.models import OrderLock


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


def create_db(dbname: str = ":memory:") -> Union[Database, None]:
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
                           (
                           symbol text, side text, quantity integer,
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
                           cancel_after_expiry text, retries integer, max_modifications integer,
                           exchange text, tag string, can_peg integer,
                           pseudo_id string, strategy_id string, portfolio_id string,
                           JSON text, error text, is_multi integer,
                           last_updated_at text
                           )"""
            )
            return Database(con)
    except Exception as e:
        logging.error(e)
        return None


class Order(BaseModel):
    """
    The basic Order Class
    _attrs
        attributes to update when data received from broker
    _frozen_attrs
        attributes frozen; cannot be changed when modifying orders
    """

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
    timezone: str = "local"
    client_id: Optional[str] = None
    convert_to_market_after_expiry: bool = False
    cancel_after_expiry: bool = True
    retries: int = 0
    max_modifications: int = 10
    exchange: Optional[str] = None
    tag: Optional[str] = None
    connection: Optional[Database] = None
    can_peg: bool = True
    pseudo_id: Optional[str] = None
    strategy_id: Optional[str] = None
    portfolio_id: Optional[str] = None
    JSON: Optional[Json] = None
    error: Optional[str] = None
    is_multi: bool = False
    last_updated_at: Optional[pendulum.DateTime] = None
    _num_modifications: int = 0
    _attrs: Tuple[str, ...] = (
        "exchange_timestamp",
        "exchange_order_id",
        "status",
        "filled_quantity",
        "pending_quantity",
        "disclosed_quantity",
        "average_price",
    )
    _exclude_fields: Set[str] = {"connection"}
    _lock: Optional[OrderLock] = None
    _frozen_attrs: Set[str] = {"symbol", "side"}

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True

    def __init__(self, **data) -> None:
        super().__init__(**data)
        from omspy.base import Broker

        if not (self.id):
            self.id = uuid.uuid4().hex
        tz = self.timezone
        if not (self.timestamp):
            self.timestamp = pendulum.now(tz=tz)
        self.pending_quantity = self.quantity
        if self.expires_in == 0:
            self.expires_in = (
                pendulum.today(tz=tz).end_of("day") - pendulum.now(tz=tz)
            ).seconds
        else:
            self.expires_in = abs(self.expires_in)
        if self._lock is None:
            self._lock = OrderLock()

    @validator("quantity", always=True, allow_reuse=True)
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
        # Order not pending if it is complete/canceled or rejected
        # irrespective of the filled and remaining quantity
        if self.status in ("COMPLETE", "CANCELED", "REJECTED"):
            return False
        elif quantity < self.quantity:
            return True
        else:
            return False

    @property
    def is_done(self) -> bool:
        """
        returns True if the order is either COMPLETE or CANCELED or REJECTED else False
        """
        if self.is_complete:
            return True
        elif self.status in ("CANCELLED", "CANCELED", "REJECTED"):
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

    @property
    def lock(self) -> OrderLock:
        if self._lock is None:
            self._lock = OrderLock()
        return self._lock

    def _get_other_args_from_attribs(
        self, broker: Any, attribute: str, attribs_to_copy: Optional[Iterable] = None
    ) -> Dict[str, str]:
        """
        Get other arguments for the order from attributes
        broker
            valid broker instance
        attribute
            attribute to search for in broker
        attribs_to_copy
            extra attributes to be copied
        Note
        ----
        1) The broker instance is first searched for the valid attribute and it is overriden with attribs_to_copy
        """
        if attribs_to_copy is None:
            attribs_to_copy = set()
        else:
            # Convert any iterable
            attribs_to_copy = set([x for x in attribs_to_copy])
        if hasattr(broker, attribute):
            attribs = getattr(broker, attribute)
            for attrib in attribs:
                attribs_to_copy.add(attrib)
        other_args = dict()
        if attribs_to_copy:
            for key in attribs_to_copy:
                if hasattr(self, key):
                    value = getattr(self, key)
                    if value:
                        other_args[key] = value
        return other_args

    def update(self, data: Dict[str, Any], save: bool = True) -> bool:
        """
        Update order based on information received from broker
        data
            data to update as dictionary
        returns True if update is done
        Note
        ----
        1) Information is updated only for those keys specified in attrs
        2) Information is updated only when the order is still pending; completed/rejected/canceled orders not updated
        3) Update pending quantity if it is not in data
        """
        if not (self.is_done):
            for att in self._attrs:
                val = data.get(att)
                if val:
                    setattr(self, att, val)
            self.last_updated_at = pendulum.now(tz=self.timezone)
            if not ("pending_quantity" in data):
                self.pending_quantity = self.quantity - self.filled_quantity
            if self.connection and save:
                self.save_to_db()
            return True
        else:
            return False

    def execute(
        self, broker: Any, attribs_to_copy: Optional[Set] = None, **kwargs
    ) -> Optional[str]:
        """
        Execute an order on a broker, place a new order
        kwargs
            Additional arguments to the order
        Note
        ----
        Only new arguments added to the order in keyword arguments
        """
        # Do not place a new order if this order is complete or has order_id

        from omspy.base import Broker as base_broker

        other_args = self._get_other_args_from_attribs(
            broker, attribute="attribs_to_copy_execute", attribs_to_copy=attribs_to_copy
        )
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
            order_args.update(other_args)
            order_args.update(dct)
            order_id = broker.order_place(**order_args)
            self.order_id = order_id
            if self.connection:
                self.save_to_db()
            return order_id
        else:
            return self.order_id

    def modify(
        self, broker: Any, attribs_to_copy: Optional[Tuple] = None, **kwargs
    ) -> None:
        """
        Modify an existing order
        broker
            broker to execute the order
        attribs
            attributes to be copied from the order
        kwargs
            keyword arguments for modification
        Note
        ----
        1)resolution for order args - default arguments are created for modify, attribs_to_copy are added next and finally kwargs are updated. If the same attribute is found in all three, the user provided kwargs wins
        """
        if not (self.lock.can_modify):
            logging.debug(
                f"Order not modified since lock is modified till {self.lock.modification_lock_till}"
            )
            return
        other_args = self._get_other_args_from_attribs(
            broker, attribute="attribs_to_copy_modify", attribs_to_copy=attribs_to_copy
        )
        args_to_add = dict()
        keys = [
            "order_id",
            "quantity",
            "price",
            "trigger_price",
            "order_type",
            "disclosed_quantity",
        ]
        for k, v in kwargs.items():
            if k not in self._frozen_attrs:
                if hasattr(self, k):
                    setattr(self, k, v)
                    if k not in keys:
                        args_to_add[k] = v
                else:
                    other_args[k] = v
        order_args = {
            "order_id": self.order_id,
            "quantity": self.quantity,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "order_type": self.order_type.upper(),
            "disclosed_quantity": self.disclosed_quantity,
        }
        order_args.update(other_args)
        order_args.update(args_to_add)
        if self._num_modifications < self.max_modifications:
            broker.order_modify(**order_args)
            self._num_modifications += 1
        else:
            logging.info(f"Maximum number of modifications exceeded")

    def cancel(self, broker: Any, attribs_to_copy: Optional[Set] = None) -> None:
        """
        Cancel an existing order
        """
        if not (self.lock.can_cancel):
            logging.debug(
                f"Order not canceled since lock is modified till {self.lock.cancellation_lock_till}"
            )
            return
        other_args = self._get_other_args_from_attribs(
            broker, attribute="attribs_to_copy_cancel", attribs_to_copy=attribs_to_copy
        )
        if self.order_id is not None:
            broker.order_cancel(order_id=self.order_id, **other_args)

    def save_to_db(self) -> bool:
        """
        save or update the order to db
        """
        if self.connection:
            values = self.dict(exclude=self._exclude_fields)
            self.connection["orders"].upsert(values, pk="id")
            return True
        else:
            logging.info("No valid database connection")
            return False

    def clone(self):
        """
        Clone the order with a new order id
        Note
        ----
        returns a copy of the new order with a new
        order_id. parent_id is not copied
        """
        dct = self.dict(exclude={"id", "parent_id", "timestamp"})
        order = Order(**dct)
        return order

    def add_lock(self, code: int, seconds: float):
        """
        Create a lock on modify or cancel function
        code
            1 to lock modify and 2 to lock cancel
        seconds
            duration to lock the function
        Note
        ----
        1) Lock is created only on modify or cancel
        """
        if code == 1:
            self.lock.modify(seconds=seconds)
        elif code == 2:
            self.lock.cancel(seconds=seconds)


class CompoundOrder(BaseModel):
    """
    A collection of orders
    Note
    ----
    1) Indexes are added automatically based on the highest key value
    2) An error is raised if the index value is already used
    """

    broker: Any
    id: Optional[str] = None
    ltp: defaultdict = Field(default_factory=defaultdict)
    orders: List[Order] = Field(default_factory=list)
    connection: Optional[Database] = None
    order_args: Optional[Dict] = None
    _index: Dict[int, Order] = PrivateAttr(default_factory=defaultdict)
    _keys: Dict[Hashable, Order] = PrivateAttr(default_factory=defaultdict)

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if not (self.id):
            self.id = uuid.uuid4().hex
        if self.order_args is None:
            self.order_args = {}
        if self.orders:
            for i, o in enumerate(self.orders):
                self._index[i] = o

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

    def _get_next_index(self) -> int:
        idx = max(self._index.keys()) + 1 if self._index else 0
        return idx

    def _get_by_key(self, key: Hashable) -> Union[Order, None]:
        return self._keys.get(key)

    def _get_by_index(self, index: int) -> Union[Order, None]:
        return self._index.get(index)

    def get(self, key: Hashable) -> Union[Order, None]:
        """
        Get the order by key or index
        key
            index or key
        returns Order if available or None
        Note
        ----
        1) key is first searched in key and then searched in index
        2) index starts at zero
        """
        order = self._get_by_key(key)
        if order is None:
            try:
                if isinstance(key, (str, int)):
                    int_key = int(key)
                    return self._get_by_index(int_key)
                else:
                    return None
            except Exception as e:
                return None
        else:
            return order

    def add_order(self, **kwargs) -> Optional[str]:
        kwargs["parent_id"] = self.id
        index = kwargs.pop("index", self._get_next_index())
        key = kwargs.pop("key", None)
        if not (kwargs.get("connection")):
            kwargs["connection"] = self.connection
        if index in self._index:
            raise IndexError("Order already assigned to this index")
        if key:
            if key in self._keys:
                raise KeyError("Order already assigned to this key")
        order = Order(**kwargs)
        self.orders.append(order)
        self._index[index] = order
        if key:
            self._keys[key] = order
        order.save_to_db()
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

    def check_flags(self) -> None:
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

    def add(
        self, order: Order, index: Optional[int] = None, key: Optional[Hashable] = None
    ) -> Optional[str]:
        """
        Add an order to the existing compound order
        """
        order.parent_id = self.id
        if not (order.connection):
            order.connection = self.connection
        if not (order.id):
            order.id = uuid.uuid4().hex
        if index is None:
            index = self._get_next_index()
        index = int(index)
        if index in self._index:
            raise IndexError("Order already assigned to this index")
        if key:
            if key in self._keys:
                raise KeyError("Order already assigned to this key")
        self.orders.append(order)
        self._index[index] = order
        if key:
            self._keys[key] = order
        order.save_to_db()
        return order.id

    def save(self) -> None:
        """
        Save all orders to database
        """
        if self.count > 0:
            for order in self.orders:
                order.save_to_db()


class OrderStrategy(BaseModel):
    """
    An order strategy is a list of strategies that
    is made up of a list of compound orders
    """

    broker: Any
    id: Optional[str] = None
    ltp: defaultdict = Field(default_factory=defaultdict)
    orders: List[CompoundOrder] = Field(default_factory=list)

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True

    def __init__(self, **data) -> None:
        super().__init__(**data)
        if not (self.id):
            self.id = uuid.uuid4().hex

    @property
    def positions(self) -> Counter:
        c: Counter = Counter()
        for order in self.orders:
            pos = order.positions
            c.update(pos)
        return c

    def update_ltp(self, last_price: Dict[str, float]):
        for symbol, ltp in last_price.items():
            self.ltp[symbol] = ltp
        for order in self.orders:
            order.update_ltp(last_price)
        return self.ltp

    def update_orders(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        Update all orders
        data
            data as dictionary with key as broker order_id
        """
        for order in self.orders:
            order.update_orders(data)

    @property
    def mtm(self) -> Counter:
        c: Counter = Counter()
        for order in self.orders:
            mtm = order.mtm
            c.update(mtm)
        return c

    def run(self, ltp: Dict[str, float]) -> None:
        """
        Run all orders with the given data
        ltp
            last price data as a dictionary
        """
        for order in self.orders:
            if hasattr(order, "run"):
                if callable(getattr(order, "run")):
                    order.run(ltp)

    def add(self, order: CompoundOrder) -> None:
        """
        Add a compound order to the existing strategy
        """
        self.orders.append(order)

    def save(self) -> None:
        """
        Save all orders to database
        Note
        ----
        1) Orders are saved based on the preferences of each compound order; so this doesn't save everything
        """
        for order in self.orders:
            order.save()
        pass
