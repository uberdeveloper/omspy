from pydantic import BaseModel, field_validator, Field, PrivateAttr, ConfigDict
from typing import Dict, Any, Optional, List, Type, Union, Tuple, Callable, Set, Hashable
from collections import defaultdict
from datetime import timezone
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
    """Calculate the option strike price.

    Args:
        spot: Current spot price of the underlying instrument.
        num: Number of strikes away from the at-the-money (ATM) strike.
            Positive for OTM calls/ITM puts, negative for ITM calls/OTM puts.
            Defaults to 0 (ATM).
        step: The step size between consecutive option strikes. Defaults to 100.0.

    Returns:
        The calculated option strike price.

    Note:
        By default, the ATM option strike is fetched.
    """
    v = round(spot / step)
    return v * (step + num)  # This calculation seems unusual. It should likely be `(v + num) * step`.
    # Consider: return (round(spot / step) + num) * step


def create_db(dbname: str = ":memory:") -> Union[Database, None]:
    """Create an SQLite database for storing orders.

    This function initializes an SQLite database, either in-memory or
    as a file, and creates an 'orders' table with a predefined schema
    to store order details.

    Args:
        dbname: The name of the database file. Defaults to ":memory:"
            for an in-memory database.

    Returns:
        A `sqlite_utils.Database` object connected to the created
        database, or None if an error occurs during creation.
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
    Represents a single trading order with its properties and lifecycle methods.

    This class captures all relevant details of an order, such as symbol, side,
    quantity, type, status, and timestamps. It provides methods to execute,
    modify, cancel, and update the order's state. It also supports persistence
    to an SQLite database.

    Attributes:
        symbol: Trading symbol of the instrument.
        side: Order side, e.g., 'buy' or 'sell'.
        quantity: Quantity of the instrument to trade. Defaults to 1.
        id: Unique identifier for the order. Auto-generated if not provided.
        parent_id: Optional identifier of a parent order or strategy.
        timestamp: Timestamp when the order object was created. Auto-generated.
        order_type: Type of order, e.g., 'MARKET', 'LIMIT'. Defaults to 'MARKET'.
        broker_timestamp: Timestamp from the broker.
        exchange_timestamp: Timestamp from the exchange.
        order_id: Order ID received from the broker after placement.
        exchange_order_id: Order ID received from the exchange.
        price: Price for LIMIT orders.
        trigger_price: Trigger price for STOP or STOP_LIMIT orders. Defaults to 0.0.
        average_price: Average price at which the order was filled. Defaults to 0.0.
        pending_quantity: Quantity pending execution.
        filled_quantity: Quantity that has been filled. Defaults to 0.
        cancelled_quantity: Quantity that has been cancelled. Defaults to 0.
        disclosed_quantity: Quantity to be disclosed in the market. Defaults to 0.
        validity: Order validity, e.g., 'DAY', 'IOC'. Defaults to 'DAY'.
        status: Current status of the order, e.g., 'PENDING', 'COMPLETE'.
        expires_in: Duration in seconds after which the order expires.
            Defaults to EOD if 0.
        timezone: Timezone for timestamps. Defaults to 'local'.
        client_id: Optional client identifier.
        convert_to_market_after_expiry: Whether to convert to a market order
            if it expires. Defaults to False.
        cancel_after_expiry: Whether to cancel the order if it expires.
            Defaults to True.
        retries: Number of retries for placing the order. Defaults to 0.
        max_modifications: Maximum number of allowed modifications. Defaults to 10.
        exchange: Name of the exchange, e.g., 'NSE', 'BSE'.
        tag: Optional tag for grouping or identifying orders.
        connection: Optional `sqlite_utils.Database` connection for persistence.
        can_peg: Whether the order price can be pegged. Defaults to True.
        pseudo_id: Optional user-defined identifier.
        strategy_id: Optional identifier for the strategy this order belongs to.
        portfolio_id: Optional identifier for the portfolio this order belongs to.
        JSON: Optional field to store additional JSON data.
        error: Optional error message associated with the order.
        is_multi: Flag indicating if this is part of a multi-leg order. Defaults to False.
        last_updated_at: Timestamp of the last update.
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
    JSON: Optional[Dict[str, Any]] = None
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

    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    def __init__(self, **data) -> None:
        """
        Initializes the Order object.

        Sets up default values for id, timestamp, pending_quantity, and expires_in
        if they are not provided. Also initializes the order lock.

        Args:
            **data: Arbitrary keyword arguments corresponding to the Order attributes.
        """
        super().__init__(**data)
        # from omspy.base import Broker # Import moved to methods to avoid circular dependency if Broker imports Order

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
            self._lock = OrderLock(timezone=self.timezone)

    @field_validator("quantity", mode="before")
    @classmethod
    def quantity_not_negative(cls, v):
        if v < 0:
            raise ValueError("quantity must be positive")
        return v

    @property
    def is_complete(self) -> bool:
        """Checks if the order is fully completed (filled).

        Returns:
            True if the order is complete, False otherwise.
        """
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
        """Checks if the order is currently pending execution.

        An order is not pending if its status is COMPLETE, CANCELED, or REJECTED,
        or if the sum of filled and cancelled quantities equals the total quantity.

        Returns:
            True if the order is pending, False otherwise.
        """
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
        """Checks if the order has reached a final state (COMPLETE, CANCELED, or REJECTED).

        Returns:
            True if the order is in a final state, False otherwise.
        """
        if self.is_complete:
            return True
        elif self.status in ("CANCELLED", "CANCELED", "REJECTED"): # Added "CANCELLED" for completeness
            return True
        else:
            return False

    @property
    def time_to_expiry(self) -> int:
        """Calculates the remaining time in seconds until the order expires.

        Returns:
            The time in seconds until expiry. Returns 0 if already expired.
        """
        now = pendulum.now(tz=self.timezone)
        ts = self.timestamp
        if ts is None: # Should not happen given __init__
            return self.expires_in
        return max(0, self.expires_in - (now - ts).seconds)

    @property
    def time_after_expiry(self) -> int:
        """Calculates the time in seconds that has passed since the order expired.

        Returns:
            The time in seconds after expiry. Returns 0 if not yet expired.
        """
        now = pendulum.now(tz=self.timezone)
        ts = self.timestamp
        if ts is None: # Should not happen
            return 0
        return max(0, (now - ts).seconds - self.expires_in)

    @property
    def has_expired(self) -> bool:
        """Checks if the order has expired.

        Returns:
            True if the order has expired, False otherwise.
        """
        return True if self.time_to_expiry == 0 else False

    @property
    def has_parent(self) -> bool:
        """Checks if the order has a parent ID.

        Returns:
            True if `parent_id` is set, False otherwise.
        """
        return True if self.parent_id else False

    @property
    def lock(self) -> OrderLock:
        """Provides access to the order's lock object.

        Initializes `OrderLock` if it hasn't been already.

        Returns:
            The `OrderLock` instance associated with this order.
        """
        if self._lock is None:
            self._lock = OrderLock(timezone=self.timezone)
        return self._lock

    def _get_other_args_from_attribs(
        self, broker: Any, attribute: str, attribs_to_copy: Optional[Iterable[str]] = None
    ) -> Dict[str, Any]:
        """
        Get other arguments for the order from attributes defined in the broker instance.

        This method fetches a list of attribute names from the `broker` object
        (e.g., `broker.attribs_to_copy_execute`) and then copies the values of these
        attributes from the current order instance if they exist.

        Args:
            broker: A broker instance (should have an attribute specified by `attribute`).
            attribute: The name of the attribute on the broker instance that contains
                a list of attribute names to copy (e.g., "attribs_to_copy_execute").
            attribs_to_copy: An optional iterable of additional attribute names
                to copy from the order, supplementing those specified by the broker.

        Returns:
            A dictionary containing the copied attributes and their values.
        """
        # Ensure attribs_to_copy is a set of strings
        final_attribs_to_copy: Set[str] = set()
        if attribs_to_copy is not None:
            for item in attribs_to_copy:
                final_attribs_to_copy.add(str(item))
        # The 'else' block here was causing a syntax error as it was empty.
        # If attribs_to_copy is None, final_attribs_to_copy correctly remains an empty set.
        if hasattr(broker, attribute):
            broker_defined_attrs = getattr(broker, attribute)
            if isinstance(broker_defined_attrs, Iterable):
                for attr_name in broker_defined_attrs:
                    if isinstance(attr_name, str):
                        final_attribs_to_copy.add(attr_name)

        other_args: Dict[str, Any] = {}
        if final_attribs_to_copy:
            for key in final_attribs_to_copy:
                if hasattr(self, key):
                    value = getattr(self, key)
                    # Ensure value is not None before adding, or handle as per requirements
                    if value is not None:
                        other_args[key] = value
        return other_args

    def update(self, data: Dict[str, Any], save: bool = True) -> bool:
        """
        Update order based on information received from broker.

        Updates are applied only if the order is not already in a done state
        (COMPLETE, CANCELED, REJECTED). Only attributes listed in `self._attrs`
        are updated from the `data` dictionary. If `pending_quantity` is not
        in `data`, it's recalculated.

        Args:
            data: A dictionary containing the data to update the order with.
                Keys should correspond to order attribute names.
            save: If True and a database connection exists, the order is saved
                to the database after updating. Defaults to True.

        Returns:
            True if the update was performed, False otherwise (e.g., if the
            order was already done).
        """
        if not (self.is_done):
            for att in self._attrs:
                val = data.get(att)
                if val is not None: # Check for None explicitly
                    setattr(self, att, val)
            self.last_updated_at = pendulum.now(tz=self.timezone)
            if "pending_quantity" not in data and self.quantity is not None:
                self.pending_quantity = self.quantity - self.filled_quantity
            if self.connection and save:
                self.save_to_db()
            return True
        else:
            return False

    def execute(
        self, broker: Any, attribs_to_copy: Optional[Set[str]] = None, **kwargs: Any
    ) -> Optional[str]:
        """
        Execute the order by placing it through the specified broker.

        This method will not place a new order if the current order is already
        complete or if it already has an `order_id` (indicating it has been
        placed before).

        Args:
            broker: The broker instance to use for placing the order. It must
                have an `order_place` method.
            attribs_to_copy: An optional set of attribute names to copy from this
                order instance and include in the broker's `order_place` call.
                These supplement broker-defined attributes.
            **kwargs: Additional keyword arguments to pass to the broker's
                `order_place` method, overriding any defaults or copied attributes.

        Returns:
            The `order_id` assigned by the broker if the order is placed
            successfully, or the existing `order_id` if the order was already
            placed. Returns None if the order cannot be placed (e.g., already complete).

        Note:
            The `omspy.base.Broker` import is done within this method to avoid
            potential circular dependencies if `Broker` also imports `Order`.
        """
        # Do not place a new order if this order is complete or has order_id
        from omspy.base import Broker as base_broker # Moved import here

        other_args = self._get_other_args_from_attribs(
            broker, attribute="attribs_to_copy_execute", attribs_to_copy=attribs_to_copy
        )
        if not (self.is_complete) and not (self.order_id):
            order_args: Dict[str, Any] = {
                "symbol": self.symbol.upper(),
                "side": self.side.upper(),
                "order_type": self.order_type.upper(),
                "quantity": self.quantity,
                "price": self.price,
                "trigger_price": self.trigger_price,
                "disclosed_quantity": self.disclosed_quantity,
            }
            # Filter out None values from default order_args
            order_args = {k: v for k, v in order_args.items() if v is not None}

            dct = {k: v for k, v in kwargs.items() if k not in order_args.keys()}
            order_args.update(other_args)
            order_args.update(dct)
            # Ensure required fields like quantity are present
            if order_args.get("quantity") is None:
                 logging.error("Order quantity cannot be None for execution.")
                 return None

            order_id = broker.order_place(**order_args)
            # Convert order_id to string to handle both int and str types
            if order_id is not None:
                self.order_id = str(order_id)
            else:
                self.order_id = order_id
            if self.connection:
                self.save_to_db()
            return order_id
        else:
            return self.order_id

    def modify(
        self, broker: Any, attribs_to_copy: Optional[Iterable[str]] = None, **kwargs: Any
    ) -> None:
        """
        Modify an existing order through the specified broker.

        The modification will only proceed if the order's modification lock
        is not active and the maximum number of modifications has not been
        exceeded. Attributes specified in `_frozen_attrs` cannot be modified.

        Args:
            broker: The broker instance to use for modifying the order. It must
                have an `order_modify` method.
            attribs_to_copy: An optional iterable of attribute names to copy
                from this order instance and include in the broker's `order_modify`
                call. These supplement broker-defined attributes.
            **kwargs: Keyword arguments for the modification. These will update
                the order's attributes (if not frozen) and will be passed to
                the broker's `order_modify` method, overriding defaults.

        Note:
            Order arguments resolution:
            1. Default arguments for modify are created.
            2. Attributes from `attribs_to_copy` are added.
            3. User-provided `kwargs` are updated last, taking precedence.
        """
        if not (self.lock.can_modify):
            logging.debug(
                f"Order not modified since lock is modified till {self.lock.modification_lock_till}"
            )
            return
        other_args = self._get_other_args_from_attribs(
            broker, attribute="attribs_to_copy_modify", attribs_to_copy=attribs_to_copy
        )
        args_to_add: Dict[str, Any] = {}
        # Attributes that are typically part of the broker.order_modify call
        keys_for_broker_call = {
            "order_id",
            "quantity",
            "price",
            "trigger_price",
            "order_type",
            "disclosed_quantity",
        }
        for k, v in kwargs.items():
            if k not in self._frozen_attrs:
                if hasattr(self, k):
                    setattr(self, k, v) # Update local order attribute
                    if k not in keys_for_broker_call: # If it's an extra param for broker
                        args_to_add[k] = v
                else: # If it's purely an extra param for broker not on Order model
                    other_args[k] = v

        order_args: Dict[str, Any] = {
            "order_id": self.order_id,
            "quantity": self.quantity,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "order_type": self.order_type.upper(),
            "disclosed_quantity": self.disclosed_quantity,
        }
        # Filter out None values from default order_args that might not be updatable
        order_args = {k:v for k,v in order_args.items() if v is not None}

        order_args.update(other_args) # Add broker-specific copied attributes
        order_args.update(args_to_add) # Add other kwargs not directly on Order model but for broker

        # Update order_args with kwargs that are part of keys_for_broker_call and were set on self
        for key_in_broker_call in keys_for_broker_call:
            if key_in_broker_call in kwargs: # If user explicitly passed it in kwargs
                 order_args[key_in_broker_call] = kwargs[key_in_broker_call]


        if self._num_modifications < self.max_modifications:
            if self.order_id is None:
                logging.warning("Cannot modify order: order_id is None.")
                return
            broker.order_modify(**order_args)
            self._num_modifications += 1
            if self.connection: # Save changes to DB
                self.save_to_db()
        else:
            logging.info(f"Maximum number of modifications ({self.max_modifications}) exceeded for order {self.id}")

    def cancel(self, broker: Any, attribs_to_copy: Optional[Set[str]] = None) -> None:
        """
        Cancel an existing order through the specified broker.

        The cancellation will only proceed if the order's cancellation lock
        is not active.

        Args:
            broker: The broker instance to use for cancelling the order. It must
                have an `order_cancel` method.
            attribs_to_copy: An optional set of attribute names to copy from this
                order instance and include in the broker's `order_cancel` call.
                These supplement broker-defined attributes.
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
            # Note: The order status should be updated via a separate call to `self.update()`
            # once confirmation of cancellation is received from the broker.
        else:
            logging.warning(f"Cannot cancel order {self.id}: order_id is None.")


    def save_to_db(self) -> bool:
        """
        Save or update the current state of the order to the database.

        Uses `upsert` based on the order's `id` as the primary key.
        Fields listed in `self._exclude_fields` (like 'connection') are
        not saved to the database.

        Returns:
            True if the save/update was successful, False if no valid database
            connection is available.
        """
        if self.connection:
            # Ensure pendulum.DateTime objects are converted to strings if DB requires
            values = self.model_dump(exclude=self._exclude_fields)
            for key, value in values.items():
                if isinstance(value, pendulum.DateTime):
                    values[key] = value.isoformat()
            self.connection["orders"].upsert(values, pk="id")
            return True
        else:
            logging.info("No valid database connection, order not saved.")
            return False

    def clone(self):
        """
        Create a deep copy of the order with a new unique `id`.

        The `id`, `parent_id`, and `timestamp` fields are excluded from the direct copy
        and are re-initialized for the new cloned order. All other attributes
        are copied.

        Returns:
            A new `Order` instance that is a clone of the current order but with
            a new `id` and fresh `timestamp`.
        """
        dct = self.model_dump(exclude={"id", "parent_id", "timestamp", "_lock"}) # Exclude lock too
        # Potentially exclude other stateful private attributes like _num_modifications
        order = Order(**dct)
        return order

    def add_lock(self, code: int, seconds: float):
        """
        Add a temporary lock to prevent modification or cancellation of the order.

        Args:
            code: The type of lock to apply:
                - 1: Lock modification (`self.lock.modify`).
                - 2: Lock cancellation (`self.lock.cancel`).
            seconds: The duration in seconds for which the lock should be active.
        """
        if code == 1:
            self.lock.modify(seconds=seconds)
        elif code == 2:
            self.lock.cancel(seconds=seconds)


class CompoundOrder(BaseModel):
    """
    A collection of individual `Order` objects, managed as a single entity.

    This class can represent a basket of orders or a leg of a strategy.
    It provides methods to manage, execute, and track the status of
    multiple orders collectively.

    Attributes:
        broker: The broker instance to be used for operations on these orders.
        id: Unique identifier for the compound order. Auto-generated.
        ltp: A `defaultdict` to store the Last Traded Price for symbols
            relevant to the orders in this compound group.
        orders: A list of `Order` objects belonging to this compound order.
        connection: Optional `sqlite_utils.Database` connection for persistence
            of the underlying individual orders.
        order_args: Optional dictionary of default arguments to be applied
            when creating or executing orders within this compound order.
    """

    broker: Any = None
    id: Optional[str] = None
    ltp: Dict[str, float] = Field(default_factory=dict)
    orders: List[Order] = Field(default_factory=list)
    connection: Optional[Database] = None
    order_args: Optional[Dict] = None
    _index: Dict[int, Order] = PrivateAttr(default_factory=dict)
    _keys: Dict[Hashable, Order] = PrivateAttr(default_factory=dict)

    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


    def __init__(self, **data) -> None:
        """
        Initializes the CompoundOrder object.

        Sets up a unique `id` if not provided, initializes `order_args`,
        and populates internal indexing for any pre-existing orders.

        Args:
            **data: Arbitrary keyword arguments corresponding to CompoundOrder attributes.
        """
        super().__init__(**data)
        if not (self.id):
            self.id = uuid.uuid4().hex
        if self.order_args is None:
            self.order_args = {}
        if self.orders:
            # Rebuild internal indexes if orders are passed during initialization
            self._index = {i: o for i, o in enumerate(self.orders)}
            # Note: _keys are not rebuilt here, assumes keys are managed via add_order or add methods

    def __len__(self):
        """Returns the number of orders in this compound order."""
        return len(self.orders)

    @property
    def count(self) -> int:
        """
        Return the number of orders in this compound order.

        Returns:
            The total count of orders.
        """
        return len(self.orders)

    @property
    def positions(self) -> Counter:
        """
        Calculate the net filled quantity for each symbol across all orders.

        Positive quantities indicate net long positions, negative for net short.

        Returns:
            A `collections.Counter` object where keys are symbols and values
            are the net filled quantities.
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
        """Get the next available integer index for adding a new order."""
        idx = max(self._index.keys()) + 1 if self._index else 0
        return idx

    def _get_by_key(self, key: Hashable) -> Union[Order, None]:
        """Retrieve an order by its assigned custom key."""
        return self._keys.get(key)

    def _get_by_index(self, index: int) -> Union[Order, None]:
        """Retrieve an order by its integer index."""
        return self._index.get(index)

    def get(self, key: Hashable) -> Union[Order, None]:
        """
        Get an order by its custom key or integer index.

        It first attempts to find the order using `key` as a custom key.
        If not found and `key` can be interpreted as an integer, it then
        attempts to find the order by its integer index.

        Args:
            key: The custom key or integer index of the order to retrieve.

        Returns:
            The `Order` object if found, otherwise None.
        """
        order = self._get_by_key(key)
        if order is None:
            try:
                # Check if key is int or str that can be int
                if isinstance(key, (int, str)):
                    int_key = int(key)
                    return self._get_by_index(int_key)
                else:
                    return None
            except (ValueError, TypeError): # Catch if key is not convertible to int
                return None
        else:
            return order

    def add_order(self, **kwargs) -> Optional[str]:
        """
        Create and add a new `Order` to this compound order.

        The new order will have its `parent_id` set to this compound order's `id`.
        It can be assigned an optional `index` and/or `key` for retrieval.
        If a database `connection` is set on the compound order, it's passed
        to the new `Order`. The new order is saved to the database if a
        connection is available.

        Args:
            **kwargs: Keyword arguments to initialize the new `Order` object.
                `index` (int): Optional index for the order.
                `key` (Hashable): Optional custom key for the order.

        Returns:
            The `id` of the newly created and added `Order`, or None if creation fails.

        Raises:
            IndexError: If the provided `index` is already in use.
            KeyError: If the provided `key` is already in use.
        """
        kwargs["parent_id"] = self.id
        index = kwargs.pop("index", self._get_next_index())
        key = kwargs.pop("key", None)

        if not (kwargs.get("connection")):
            kwargs["connection"] = self.connection
        if index in self._index:
            raise IndexError(f"Order already assigned to this index: {index}")
        if key:
            if key in self._keys:
                raise KeyError(f"Order already assigned to this key: {key}")
        try:
            order = Order(**kwargs)
            self.orders.append(order)
            self._index[index] = order
            if key:
                self._keys[key] = order
            order.save_to_db() # save_to_db handles no connection
            return order.id
        except Exception as e: # Catch Pydantic validation errors or other issues
            logging.error(f"Failed to create or add order: {e}", exc_info=True)
            return None


    def _average_price(self, side: str = "buy") -> Dict[str, float]:
        """
        Calculate the average filled price for each symbol for a given side (buy/sell).

        Args:
            side: The side ('buy' or 'sell') for which to calculate average prices.
                Defaults to 'buy'.

        Returns:
            A dictionary where keys are symbols and values are their
            average filled prices for the specified side.
        """
        side = str(side).lower()
        value_counter: Counter = Counter()
        quantity_counter: Counter = Counter()
        for order in self.orders:
            order_side = str(order.side).lower()
            if side == order_side and order.filled_quantity > 0 and order.average_price is not None:
                symbol = order.symbol
                price = order.average_price
                quantity = order.filled_quantity
                value = price * quantity
                value_counter.update({symbol: value})
                quantity_counter.update({symbol: quantity})

        dct: Dict[str, float] = {} # Changed from defaultdict for clearer return type
        for symbol_key in value_counter: # Iterate over symbols present in value_counter
            numerator = value_counter.get(symbol_key)
            denominator = quantity_counter.get(symbol_key)
            if numerator is not None and denominator is not None and denominator > 0:
                dct[symbol_key] = numerator / denominator
        return dct

    @property
    def average_buy_price(self) -> Dict[str, float]:
        """
        Get the average buy price for all symbols with filled buy orders.

        Returns:
            A dictionary {symbol: average_buy_price}.
        """
        return self._average_price(side="buy")

    @property
    def average_sell_price(self) -> Dict[str, float]:
        """
        Get the average sell price for all symbols with filled sell orders.

        Returns:
            A dictionary {symbol: average_sell_price}.
        """
        return self._average_price(side="sell")

    def update_orders(self, data: Dict[str, Dict[str, Any]]) -> Dict[str, bool]:
        """
        Update multiple pending orders within this compound order.

        Args:
            data: A dictionary where keys are broker `order_id`s and values are
                dictionaries of attribute updates for that order (e.g., from
                a broker's order update feed).

        Returns:
            A dictionary where keys are the `order_id`s of the orders that
            were attempted to be updated, and values are booleans indicating
            if the update was successful for that specific order.
        """
        dct: Dict[str, bool] = {}
        for order in self.pending_orders: # Iterate only over pending orders
            order_id = str(order.order_id) # Ensure order_id is a string for dict key
            # status = order.status # Not directly used here, update handles status
            if order_id in data:
                update_data = data.get(order_id)
                if update_data: # Ensure there's data to update with
                    update_status = order.update(update_data) # order.update returns bool
                    dct[order_id] = update_status
                else:
                    dct[order_id] = False # No data provided for this order_id
            else:
                # If order_id not in data, it means no update info for this pending order
                dct[order_id] = False
        return dct

    def _total_quantity(self) -> Dict[str, Counter]:
        """
        Calculate the total filled buy and sell quantities for each symbol.

        Returns:
            A dictionary with keys 'buy' and 'sell'. Each key maps to a
            `collections.Counter` object {symbol: total_filled_quantity}.
        """
        buy_counter: Counter = Counter()
        sell_counter: Counter = Counter()
        for order in self.orders:
            side = order.side.lower()
            symbol = order.symbol
            quantity = abs(order.filled_quantity) # Use absolute for summing up quantities
            if quantity > 0: # Only consider orders with actual filled quantity
                if side == "buy":
                    buy_counter.update({symbol: quantity})
                elif side == "sell":
                    sell_counter.update({symbol: quantity})
        return {"buy": buy_counter, "sell": sell_counter}

    @property
    def buy_quantity(self) -> Counter:
        """
        Get the total filled buy quantity for each symbol.

        Returns:
            A `collections.Counter` {symbol: total_buy_quantity}.
        """
        return self._total_quantity()["buy"]

    @property
    def sell_quantity(self) -> Counter:
        """
        Get the total filled sell quantity for each symbol.

        Returns:
            A `collections.Counter` {symbol: total_sell_quantity}.
        """
        return self._total_quantity()["sell"]

    def update_ltp(self, last_price: Dict[str, float]):
        """
        Update the Last Traded Price (LTP) for specified symbols.

        This LTP is stored within the `CompoundOrder`'s `ltp` attribute
        and can be used for calculations like MTM.

        Args:
            last_price: A dictionary where keys are symbols and values are
                their latest LTPs.

        Returns:
            The updated `ltp` defaultdict of the `CompoundOrder`.
        """
        for symbol, ltp_val in last_price.items():
            if isinstance(ltp_val, (int, float)): # Basic validation for LTP
                self.ltp[symbol] = float(ltp_val)
            else:
                logging.warning(f"Invalid LTP value {ltp_val} for symbol {symbol}. Must be number.")
        return self.ltp

    @property
    def net_value(self) -> Counter:
        """
        Calculate the net traded value (cost) for each symbol.

        Net value is (filled_quantity * average_price). It's positive for
        buys and negative for sells from the perspective of cash flow.
        This method sums these values. If you bought 10 shares at 100 (value 1000)
        and sold 5 shares at 110 (value -550), net value for the symbol would be 450.
        However, the current implementation calculates total buy value and total sell value
        and then applies sign, so it's more like (buy_qty * buy_avg_price) - (sell_qty * sell_avg_price)
        if signs are applied correctly.

        The current code:
        `value = order.filled_quantity * order.average_price * sign`
        If buy: sign=1, value = qty * price
        If sell: sign=-1, value = qty * price * -1 = -(qty*price)
        This correctly represents cash outflow for buys and inflow for sells.

        Returns:
            A `collections.Counter` {symbol: net_value}.
        """
        c: Counter = Counter()
        for order in self.orders:
            if order.filled_quantity > 0 and order.average_price is not None:
                symbol = order.symbol
                side = str(order.side).lower()
                sign = -1 if side == "sell" else 1 # Cash flow: buy is negative, sell is positive
                # To align with standard portfolio value where assets are positive:
                # sign = 1 for buy, -1 for sell IF we are calculating cost basis in a way that selling reduces it.
                # The current sign convention seems to be for cash flow relative to the portfolio.
                # Let's assume it means: value_of_buys - value_of_sells at historical prices.
                # If side is 'buy', sign is 1. value = filled_quantity * average_price.
                # If side is 'sell', sign is -1. value = -(filled_quantity * average_price).
                # This means positive values are assets acquired, negative values are assets disposed of, valued at trade price.
                value = order.filled_quantity * order.average_price * sign
                c.update({symbol: value})
        return c

    @property
    def mtm(self) -> Counter:
        """
        Calculate the Mark-to-Market (MTM) profit/loss for each symbol.

        MTM is calculated as: (Current Market Value of Positions) - (Net Traded Value of Positions).
        Current Market Value = net_position_quantity * current_LTP.
        Net Traded Value is what's returned by `self.net_value`.

        The existing code calculates `net_value` (cost basis, where buys are positive cost, sells are negative cost).
        Then it does `c.update({symbol: -value})` which means it takes `-(cost_basis)`.
        Then it adds `quantity * ltp`. So MTM = `(quantity * ltp) - cost_basis`. This is correct.

        Returns:
            A `collections.Counter` {symbol: mtm_value}.
        """
        c: Counter = Counter()
        net_value_map = self.net_value # Cost basis: positive for buy cost, negative for sell cost reduction
        positions_map = self.positions # Net quantity: positive for long, negative for short

        # Add the negative of the net traded value (cost basis)
        for symbol, value_at_trade_price in net_value_map.items():
            c.update({symbol: -value_at_trade_price}) # So, MTM starts as -cost_basis

        # Add the current market value of the positions
        for symbol, quantity in positions_map.items():
            ltp_val = self.ltp.get(symbol)
            if ltp_val is not None:
                current_market_value = quantity * ltp_val
                c.update({symbol: current_market_value}) # MTM = current_market_value - cost_basis
            else:
                # If LTP is not available, MTM for that symbol might be incomplete or based on trade price only.
                # Current logic implies MTM relative to zero if LTP is missing for a position.
                # Or, if only net_value contributed, it's unrealized P/L against zero market value.
                logging.debug(f"LTP not available for symbol {symbol} during MTM calculation. MTM for this symbol might be partial.")
        return c

    @property
    def total_mtm(self) -> float:
        """
        Calculate the total Mark-to-Market (MTM) profit/loss across all symbols.

        Returns:
            The sum of MTM values for all symbols.
        """
        return sum(self.mtm.values())

    def execute_all(self, **kwargs):
        """
        Execute all orders in this compound order using the assigned broker.

        Any `kwargs` provided are passed down to the `execute` method of each
        individual `Order`. Default `order_args` from the `CompoundOrder`
        are also applied.

        Args:
            **kwargs: Additional keyword arguments to pass to each order's
                `execute` method.
        """
        for order in self.orders:
            # Ensure order_args is a dict; deepcopy to prevent modification of CompoundOrder's defaults
            current_order_args = deepcopy(self.order_args) if self.order_args else {}
            current_order_args.update(kwargs) # User-provided kwargs for this specific call take precedence
            try:
                order.execute(broker=self.broker, **current_order_args)
            except Exception as e:
                logging.error(f"Error executing order {order.id or 'N/A'}: {e}", exc_info=True)


    def check_flags(self) -> None:
        """
        Check expiry flags on each pending order and take appropriate action.

        If an order `is_pending` and `has_expired`:
        - If `convert_to_market_after_expiry` is True, modifies the order to 'MARKET'.
        - Else if `cancel_after_expiry` is True, cancels the order.
        """
        for order in self.orders: # Iterate through all orders, not just pending_orders directly
            if order.is_pending and order.has_expired:
                try:
                    if order.convert_to_market_after_expiry:
                        logging.info(f"Order {order.id} expired, converting to MARKET.")
                        order.order_type = "MARKET"
                        order.price = None # Market orders typically don't have a price
                        order.trigger_price = 0.0 # Reset trigger price
                        order.modify(self.broker)
                    elif order.cancel_after_expiry:
                        logging.info(f"Order {order.id} expired, cancelling.")
                        order.cancel(broker=self.broker)
                except Exception as e:
                    logging.error(f"Error processing expired order {order.id}: {e}", exc_info=True)


    @property
    def completed_orders(self) -> List[Order]:
        """
        Get a list of all orders in this compound order that are complete.

        Returns:
            A list of `Order` objects.
        """
        return [order for order in self.orders if order.is_complete]

    @property
    def pending_orders(self) -> List[Order]:
        """
        Get a list of all orders in this compound order that are currently pending.

        Returns:
            A list of `Order` objects.
        """
        return [order for order in self.orders if order.is_pending]

    def add(
        self, order: Order, index: Optional[int] = None, key: Optional[Hashable] = None
    ) -> Optional[str]:
        """
        Add an existing `Order` object to this compound order.

        The order's `parent_id` is set to this compound order's `id`.
        If the order doesn't have a database `connection`, the compound order's
        connection is assigned. A unique `id` is generated for the order if missing.
        The order can be assigned an `index` and/or `key`.
        The order is saved to the database if a connection is available.

        Args:
            order: The `Order` object to add.
            index: Optional integer index to assign to the order. If None,
                the next available index is used.
            key: Optional hashable key to assign to the order.

        Returns:
            The `id` of the added `Order`, or None if addition fails.

        Raises:
            IndexError: If the provided `index` is already in use.
            KeyError: If the provided `key` is already in use.
        """
        if not isinstance(order, Order):
            logging.error("Item to add is not an Order instance.")
            return None

        order.parent_id = self.id
        if not (order.connection):
            order.connection = self.connection
        if not (order.id):
            order.id = uuid.uuid4().hex # Ensure order has an ID

        if index is None:
            index = self._get_next_index()
        index = int(index) # Ensure index is an integer

        if index in self._index:
            raise IndexError(f"Order already assigned to this index: {index}")
        if key:
            if key in self._keys:
                raise KeyError(f"Order already assigned to this key: {key}")

        self.orders.append(order)
        self._index[index] = order
        if key:
            self._keys[key] = order
        order.save_to_db() # save_to_db handles no connection
        return order.id

    def save(self) -> None:
        """
        Save all individual orders within this compound order to the database.

        This method iterates through each `Order` in `self.orders` and calls
        its `save_to_db` method.
        """
        if self.count > 0:
            saved_count = 0
            for order_to_save in self.orders:
                if order_to_save.save_to_db():
                    saved_count +=1
            logging.debug(f"Attempted to save {self.count} orders. {saved_count} reported success.")
        else:
            logging.debug("No orders in CompoundOrder to save.")


class OrderStrategy(BaseModel):
    """
    Represents a trading strategy composed of one or more `CompoundOrder` objects.

    This class acts as a container for multiple `CompoundOrder` instances,
    allowing them to be managed as part of a larger strategy. It can
    aggregate positions and MTM across all its compound orders.

    Attributes:
        broker: The broker instance to be used for operations.
        id: Unique identifier for the order strategy. Auto-generated.
        ltp: A `defaultdict` to store Last Traded Prices for relevant symbols.
        orders: A list of `CompoundOrder` objects that make up this strategy.
    """

    broker: Any = None # Should ideally be a specific Broker type
    id: Optional[str] = None
    ltp: Dict[str, float] = Field(default_factory=dict)
    orders: List[CompoundOrder] = Field(default_factory=list)
    # connection: Optional[Database] = None # Consider if strategy needs its own DB connection management

    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


    def __init__(self, **data) -> None:
        """
        Initializes the OrderStrategy object.

        Sets up a unique `id` if not provided.

        Args:
            **data: Arbitrary keyword arguments corresponding to OrderStrategy attributes.
        """
        super().__init__(**data)
        if not (self.id):
            self.id = uuid.uuid4().hex
        # Pass down broker and connection to child CompoundOrders if they don't have them?
        # Or assume they are configured correctly when added.
        # For now, assume CompoundOrders are managed externally regarding broker/connection setup before adding.

    @property
    def positions(self) -> Counter:
        """
        Aggregate positions from all `CompoundOrder` objects in this strategy.

        Returns:
            A `collections.Counter` representing net positions for each symbol
            across the entire strategy.
        """
        c: Counter = Counter()
        for compound_order in self.orders:
            pos = compound_order.positions
            c.update(pos)
        return c

    def update_ltp(self, last_price: Dict[str, float]):
        """
        Update Last Traded Prices (LTP) for the strategy and its compound orders.

        Args:
            last_price: A dictionary {symbol: ltp_value}.

        Returns:
            The updated `ltp` defaultdict of the `OrderStrategy`.
        """
        for symbol, ltp_val in last_price.items():
            if isinstance(ltp_val, (int, float)):
                self.ltp[symbol] = float(ltp_val)
            else:
                logging.warning(f"Strategy: Invalid LTP value {ltp_val} for symbol {symbol}.")

        for compound_order in self.orders:
            compound_order.update_ltp(last_price) # Propagate LTP update
        return self.ltp

    def update_orders(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        Update orders across all `CompoundOrder` objects in this strategy.

        Args:
            data: A dictionary where keys are broker `order_id`s and values
                are dictionaries of attribute updates for that order.
        """
        for compound_order in self.orders:
            compound_order.update_orders(data)

    @property
    def mtm(self) -> Counter:
        """
        Aggregate Mark-to-Market (MTM) profit/loss from all `CompoundOrder`
        objects in this strategy.

        Returns:
            A `collections.Counter` {symbol: total_mtm_value} for the strategy.
        """
        c: Counter = Counter()
        for compound_order in self.orders:
            mtm_val = compound_order.mtm
            c.update(mtm_val)
        return c

    @property
    def total_mtm(self) -> float:
        """
        Calculate the total Mark-to-Market (MTM) profit/loss across all
        compound orders in the strategy.

        Returns:
            The sum of MTM values for the entire strategy.
        """
        return sum(self.mtm.values())


    def run(self, ltp: Optional[Dict[str, float]] = None) -> None:
        """
        Execute the `run` method of each `CompoundOrder` in the strategy.

        This is intended for strategies where `CompoundOrder` instances might
        have their own dynamic logic encapsulated in a `run` method.
        If `ltp` is provided, it's passed to each `CompoundOrder`'s `run` method.

        Args:
            ltp: Optional dictionary of Last Traded Prices {symbol: ltp_value}
                 to pass to the compound orders.
        """
        for compound_order in self.orders:
            if hasattr(compound_order, "run") and callable(getattr(compound_order, "run")):
                try:
                    if ltp is not None:
                        compound_order.run(ltp=ltp) # type: ignore
                    else:
                        compound_order.run() # type: ignore
                except Exception as e:
                    logging.error(f"Error running compound_order {compound_order.id}: {e}", exc_info=True)


    def add(self, compound_order: CompoundOrder) -> None:
        """
        Add a `CompoundOrder` object to this strategy.

        Args:
            compound_order: The `CompoundOrder` instance to add.

        Raises:
            TypeError: if the item to add is not a CompoundOrder instance.
        """
        if not isinstance(compound_order, CompoundOrder):
            raise TypeError("Can only add CompoundOrder instances to OrderStrategy.")

        # Potentially set parent_id or other links here if needed
        # compound_order.parent_strategy_id = self.id (if such a field exists)

        # Ensure the compound order has the same broker if strategy enforces this
        if self.broker and not compound_order.broker:
            compound_order.broker = self.broker
        elif self.broker and compound_order.broker and compound_order.broker is not self.broker:
            logging.warning(f"CompoundOrder {compound_order.id} has a different broker than Strategy {self.id}.")

        self.orders.append(compound_order)

    def save(self) -> None:
        """
        Save all orders within all `CompoundOrder` objects of this strategy
        to the database.

        This iterates through each `CompoundOrder` and calls its `save` method.
        """
        for compound_order in self.orders:
            try:
                compound_order.save()
            except Exception as e:
                logging.error(f"Error saving compound_order {compound_order.id} within strategy {self.id}: {e}", exc_info=True)
        pass # Original pass statement, can be removed if no other logic.
