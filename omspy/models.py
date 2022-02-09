"""
This module contains the list of basic models
"""
from pydantic import BaseModel


class QuantityMatch(BaseModel):
    buy: int = 0
    sell: int = 0

    @property
    def is_equal(self) -> bool:
        return True if self.buy == self.sell else False

    @property
    def not_matched(self) -> int:
        return self.buy - self.sell


class BasicPosition(BaseModel):
    """
    A simple position tracking mechanism
    """

    symbol: str
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_value: float = 0.0
    sell_value: float = 0.0

    @property
    def net_quantity(self) -> int:
        return self.buy_quantity - self.sell_quantity

    @property
    def average_buy_value(self) -> float:
        return self.buy_value / self.buy_quantity if self.buy_value > 0.0 else 0.0

    @property
    def average_sell_value(self) -> float:
        return self.sell_value / self.sell_quantity if self.sell_quantity > 0 else 0.0
