"""
General utility functions for conversion and else
"""
from typing import Dict, Any, List
from omspy.models import BasicPosition
from collections import defaultdict


def create_basic_positions_from_orders_dict(
    orders: List[Dict]
) -> Dict[str, BasicPosition]:
    """
    Create a dictionary of positions from list of orders received from broker
    orders
        list of orders
    returns a dictionary with key being the symbol and values as a BasicPosition model
    """
    dct = {}
    for order in orders:
        symbol = order.get("symbol")
        if symbol:
            price = max(
                order.get("average_price", 0),
                order.get("price", 0),
                order.get("trigger_price", 0),
            )
            quantity = abs(order.get("quantity", 0))
            side = order.get("side").lower()
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
