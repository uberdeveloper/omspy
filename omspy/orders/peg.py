from typing import Optional, Dict, List, Type, Any, Union, Tuple, Callable
from omspy.base import Broker
from omspy.order import Order, CompoundOrder

class BasicPeg(CompoundOrder):
    symbol:str
    side:str
    quantity:int

    def __init__(self, **data) -> None:
        super().__init__(**data)
        order = Order(symbol=self.symbol, quantity=self.quantity,side=self.side, order_type='LIMIT')
        self.add(order)
        self.ltp[self.symbol] = 0


class PegMarket(BasicPeg):
    convert_to_market_after_expiry:bool = False
    peg_every:int = 5
    peg_limit:int = 10

