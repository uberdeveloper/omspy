"""
General utility functions for conversion and else
"""

from typing import Dict, Any, List, Union, NamedTuple
from omspy.models import BasicPosition
from collections import defaultdict
import pathlib
import yaml
import logging


class UQty(NamedTuple):
    q: float
    f: float
    p: float
    c: float


def create_basic_positions_from_orders_dict(
    orders: List[Dict],
) -> Dict[str, BasicPosition]:
    """
    Create a dictionary of positions from list of orders received from broker
    orders
        list of orders
    returns a dictionary with key being the symbol and values as a BasicPosition model
    """
    dct: Dict[str, BasicPosition] = {}
    for order in orders:
        symbol = order.get("symbol")
        if symbol:
            price = max(
                order.get("average_price", 0),
                order.get("price", 0),
                order.get("trigger_price", 0),
            )
            quantity = abs(order.get("quantity", 0))
            side = order["side"].lower()
            if symbol not in dct.keys():
                # Create symbol if it doesn't exist
                dct[symbol] = BasicPosition(symbol=symbol)
            position = dct[symbol]
            if side == "buy":
                position.buy_quantity += quantity
                position.buy_value += price * quantity
            elif side == "sell":
                position.sell_quantity += quantity
                position.sell_value += price * quantity
    return dct


def dict_filter(lst: List[Dict], **kwargs) -> List[Dict]:
    """
    Filter a list of dictionary to conditions matching
    in kwargs
    lst
        list of dictionaries
    kwargs
        key values to filter; key is the dictionary key
        and value is the value to match.
        **This is an AND filter**

    Note
    -----
    For each dictionary in the list, each of the arguments
    in kwargs are matched and only those dictionaries that
    match all the conditions are returned
    """
    if len(lst) == 0:
        print("Nothing in the list")
        return []
    new_lst = []
    for d in lst:
        case = True
        for k, v in kwargs.items():
            if d.get(k) != v:
                case = False
        if case:
            new_lst.append(d)
    return new_lst


def tick(price, tick_size=0.05):
    """
    Rounds a given price to the requested tick
    """
    return round(price / tick_size) * tick_size


def stop_loss_step_decimal(
    price: float, side: str = "B", dec: float = 0.45, step: int = 2
) -> float:
    """
    Truncates down the stop loss value to the desired step
    and adds the given decimal
    price
        stop loss price
    side
        side to place order, the actual stop loss side
        B for BUY, S for SELL
    dec
        fixed decimal to be added
    step
        step size to determine stop
    Note
    ----
    1. Step object is always a positive number
    2. Side is the actual stop loss side you are placing the order
    """
    step = abs(step)
    m = int(price / step)
    val = (m + 1.0) * step if side == "S" else (m * step) - 1.0
    val = val + 1 - dec if side == "S" else val + dec
    return val


def update_quantity(q: float, f: float, p: float, c: float) -> UQty:
    """
    Update filled,pending and canceled quantity based on the given data
    q
        actual quantity orders
    f
        filled quantity
    p
        pending quantity
    c
        canceled/rejected quantity
    returns a named tuple containing the calculated values
    Note
    -----
    1) q is taken to be the actual quantity
    2) formula used is **quantity = filled_quantity + pending_quantiy - canceled quantity**
    3) canceled quantity is given preference over other quantities, filled quantity
    the next and pending the last priority
    4) if filled or canceled quantity is greater than given quantity, it is set equal
    to the quantity and all other quantities are discarded
    """
    if c > 0:
        c = min(c, q)
        f = q - c
        p = q - c - f
    elif f > 0:
        f = min(f, q)
        p = q - f
    elif p > 0:
        p = min(p, q)
        f = q - p
    else:
        p = q - p
    return UQty(q, f, p, c)


def load_broker(
    credentials: Union[
        str, dict, list[dict], pathlib.PurePath, pathlib.Path
    ] = "credentials.yaml",
    index: int = 0,
) -> Any:
    """
    load broker based on given data in the expected format
    expected format for a broker is a dictionary with 2 keys, name and config. name is the broker module name and config is a dictionary containing arguments to the broker
    ```
    {
        "name": "broker_module_name",
        "config": {
            "api_key": "api key",
            "api_secret": "api secret",
            "access_token": "access token",
            "refresh_token": "refresh token",
            "user_id": "user id",
    }
    credentials
        string , dictionary or list of dictionaries containing broker credentials in requested format
        default filename `credentials.yaml` in the current directory
        * if credentials is a string or a pathlib path, it will be treated as filename
        * if name is a dict, then it will be treated as dictionary and the index argument is discarded
        * if name is a list, then it will be treated as list of dictionaries
    index
        index of the broker in the list
        this argument is discared if a dictionary is given
    Note
    -----
    1. This only initializes the broker, it does not authenticate the broker.
    2. the `config` key is a dictionary containing arguments specific  to a broker and it must contain arguments matching the specific broker
    3. returns `None` if the specified broker is not found
    """
    from omspy.brokers.zerodha import Zerodha
    from omspy.brokers.finvasia import Finvasia
    from omspy.brokers.icici import Icici
    from omspy.brokers.neo import Neo

    broker_mapping = {
        "zerodha": Zerodha,
        "finvasia": Finvasia,
        "icici": Icici,
        "neo": Neo,
    }

    def _load_instance(creds):
        try:
            name = creds["name"].lower()
            broker_module = broker_mapping[name]
            if broker_module:
                try:
                    broker = broker_module(**creds["config"])
                    return broker
                except Exception as e:
                    logging.error(e)
                    return
        except KeyError as e:
            logging.error(e)
            error_msg = f"""
             Broker {creds["name"]} not available.
             Available brokers are {list(broker_mapping.keys())}
             If you have this broker installed locally,
             kindly submit a pull request
             """
            raise ValueError(error_msg)

    if isinstance(credentials, str):
        with open(credentials, "r") as f:
            broker_list = yaml.safe_load(f)
        creds = broker_list[index]
        return _load_instance(creds)
    elif isinstance(credentials, (pathlib.PurePath, pathlib.Path)):
        with open(str(credentials), "r") as f:
            broker_list = yaml.safe_load(f)
        creds = broker_list[index]
        return _load_instance(creds)
    elif isinstance(credentials, dict):
        return _load_instance(credentials)
    elif isinstance(credentials, list):
        creds = credentials[index]
        return _load_instance(creds)
    else:
        raise ValueError("Invalid credentials format")
