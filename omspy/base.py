from typing import Callable, Optional, List, Dict, Tuple, Union
import inspect
import yaml
import logging
from copy import deepcopy
from omspy.utils import *
import omspy.models as models


def pre(func: Callable) -> Callable:
    """
    Decorator to run before a function call
    """
    name = func.__name__

    def f(*args, **kwargs):
        self = args[0]
        override = self.get_override(name)
        if override:
            kwargs = self.rename(kwargs, override)
        return func(*args, **kwargs)

    return f


def post(func: Callable) -> Callable:
    """
    Decorator to run after a function call
    """
    if "__name__" in dir(func):
        name = func.__name__

    def f(*args, **kwargs):
        self = args[0]
        override = self.get_override(name)
        response = func(*args, **kwargs)
        if override:
            if isinstance(response, list):
                return [self.rename(r, override) for r in response]
            elif isinstance(response, dict):
                return self.rename(response, override)
        return response

    return f


class Broker:
    """
    A metaclass implementation for live trading
    All the methods need to be overriden for
    specific brokers
    Override is a mechanism through which you could
    replace the keys of the request/response to
    match the keys of the API.
    """

    def __init__(self, **kwargs) -> None:
        """
        All initial conditions go here
        kwargs
        The following keyword arguments are supported
        is_override
            use the override option
        override_file
            path to override file
        """
        self._override = {
            "orders": {},
            "positions": {},
            "trades": {},
            "order_place": {},
            "order_cancel": {},
            "order_modify": {},
        }
        file_path = inspect.getfile(self.__class__)[:-3]
        override_file = kwargs.pop("override_file", f"{file_path}.yaml")
        try:
            with open(override_file, "r") as f:
                dct = yaml.safe_load(f)
            for k, v in dct.items():
                self.set_override(k, v)
        except FileNotFoundError:
            logging.warning("Default override file not found")

    def get_override(self, key: str):
        """
        get the override for the given key
        returns all if key is not specified
        Note
        ----
        key should be implemented as a method
        """
        return self._override.get(key, self._override.copy())

    def set_override(self, key, values):
        """
        set the overrides for the given key
        key
            key - usually a method
        values
            values for the key
        returns the key if added
        """
        self._override[key] = values
        return self.get_override(key)

    def authenticate(self):
        """
        Authenticate the user usually via an interface.
        This method takes no arguments. Any arguments
        should be passed in the __init__ method
        """
        raise NotImplementedError

    @property
    def orders(self) -> List[Dict]:
        """
        Get the list of orders
        """
        raise NotImplementedError

    @property
    def trades(self) -> List[Dict]:
        """
        Get the list of trades
        """
        raise NotImplementedError

    @property
    def positions(self) -> List[Dict]:
        """
        Get the list of positions
        """
        raise NotImplementedError

    def order_place(
        self,
        symbol: str,
        side: str,
        order_type: str = "MARKET",
        quantity: int = 1,
        **kwargs,
    ) -> str:
        """
        Place an order
        """
        raise NotImplementedError

    def order_modify(self, order_id: str, **kwargs) -> str:
        """
        Modify an order with the given order id
        """
        raise NotImplementedError

    def order_cancel(self, order_id: str) -> str:
        """
        Cancel an order with the given order id
        """
        raise NotImplementedError

    @staticmethod
    def rename(dct, keys):
        """
        rename the keys of an existing dictionary
        dct
            existing dictionary
        keys
            keys to be renamed as dictionary with
            key as existing key and value as value
            to be replaced
        Note
        -----
        A new dictionary is constructed with existing
        keys replaced by new ones. Values are not replaced.
        >>> rename({'a': 10, 'b':20}, {'a': 'aa'})
        {'aa':10, 'b': 20}
        >>> rename({'a': 10, 'b': 20}, {'c': 'm'})
        {'a':10, 'b':20}
        """
        new_dct = {}
        for k, v in dct.items():
            if keys.get(k):
                new_dct[keys[k]] = v
            else:
                new_dct[k] = v
        return new_dct

    def close_all_positions(
        self,
        positions: Optional[List[Dict]] = None,
        keys_to_copy: Optional[Tuple] = None,
        keys_to_add: Optional[Dict] = None,
        symbol_transformer: Optional[Callable] = None,
        **kwargs,
    ) -> None:
        """
        Close all existing positions.
        For all existing positions, a MARKET order in
        the opposite side is placed to force exit
        positions
            list of positions. By default, all existing positions are closed
        keys_to_copy
            keys and values to be copied from the position dictionary when placing the order
        keys_to_add
            keys to be manually added when placing the order
        symbol_transformer
            any function to be applied to transform the symbol from position; use this if the symbol in position need to be transformed before placing an order. By default, the symbol from position is used
        Note
        ----
        Use this only if you want to close all orders in a
        panic situation, or you have orders not controlled
        by the system. Do not forget to cancel the existing
        open orders

        """
        STATIC_KEYS = ["quantity", "side", "symbol", "order_type"]
        if callable(symbol_transformer):
            func = symbol_transformer
        else:
            func = lambda x: x  # just return the symbol

        if positions is None:
            positions = self.positions
        if not (keys_to_copy):
            keys_to_copy = ()
        if not (keys_to_add):
            keys_to_add = {}
        for position in positions:
            try:
                quantity = int(position.get("quantity"))
                symbol = func(position.get("symbol"))
                if quantity:
                    if quantity > 0:
                        side = "sell"
                    elif quantity < 0:
                        side = "buy"
                    order_args = {
                        "quantity": abs(quantity),
                        "side": side,
                        "symbol": symbol,
                        "order_type": "MARKET",
                    }
                    for key in keys_to_copy:
                        if key not in STATIC_KEYS:
                            if position.get(key):
                                order_args[key] = position[key]
                    final_args = {}
                    final_args.update(keys_to_add)
                    final_args.update(order_args)
                    self.order_place(**final_args)
            except Exception as e:
                logging.error(e)

    def cancel_all_orders(
        self,
        keys_to_copy: Optional[Tuple] = None,
        keys_to_add: Optional[Dict] = None,
        **kwargs,
    ) -> None:
        """
        Cancel all existing open orders
        """
        if not (keys_to_copy):
            keys_to_copy = ()
        if not (keys_to_add):
            keys_to_add = {}
        statuses = ("COMPLETE", "CANCELED", "REJECTED")
        for order in self.orders:
            status = order.get("status")
            if not (status):
                status = "PENDING"
            else:
                status = str(status).upper()
            order_id = order.get("order_id")
            if order_id and status not in statuses:
                final_args = {}
                for key in keys_to_copy:
                    final_args[key] = order.get(key)
                final_args.update(keys_to_add)
                final_args.update({"order_id": order_id})
                self.order_cancel(**final_args)

    def get_positions_from_orders(self, **kwargs) -> Dict[str, models.BasicPosition]:
        orders = self.orders
        statuses = ("CANCELED", "REJECTED")
        orders = [o for o in orders if o["status"] not in statuses]
        orders = dict_filter(orders, **kwargs)
        return create_basic_positions_from_orders_dict(orders)

    def cover_orders(
        self, stop: Union[Callable, float], order_args: Optional[Dict] = None, **kwargs
    ):
        """
        Cover orders for safety
        """

        def get_stop(side: str, price: float, stop: float = stop) -> float:
            if side == "buy":
                stop_price = price * (1 - stop)
            elif side == "sell":
                stop_price = price * (1 + stop)
            else:
                return price
            return tick(stop_price)

        if callable(stop):
            stop_function = stop
        else:
            stop_function = get_stop

        if order_args is None:
            order_args = {}

        positions = self.get_positions_from_orders(**kwargs)
        non_matched = [p for p in positions.values() if p.net_quantity != 0]
        for pos in non_matched:
            if pos.net_quantity > 0:
                stop_loss_price = stop_function(side="buy", price=pos.average_buy_value)
                # TODO: Generalize side with enum since the
                # present implementation caters to a single broker
                self.order_place(
                    symbol=pos.symbol,
                    side="SELL",
                    trigger_price=stop_loss_price,
                    order_type="SL-M",
                    quantity=abs(pos.net_quantity),
                    **order_args,
                )
            elif pos.net_quantity < 0:
                stop_loss_price = stop_function(
                    side="sell", price=pos.average_sell_value
                )
                self.order_place(
                    symbol=pos.symbol,
                    side="BUY",
                    trigger_price=stop_loss_price,
                    order_type="SL-M",
                    quantity=abs(pos.net_quantity),
                    **order_args,
                )
