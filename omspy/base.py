from typing import Callable, Optional, List, Dict
import inspect
import yaml
import logging


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

    def __init__(self, **kwargs):
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
        This methods takes no arguments. Any arguments
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
