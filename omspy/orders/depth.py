from omspy.models import Quote
from omspy.utils import tick
from typing import List
from pydantic import BaseModel


class MarketDepth(BaseModel):
    bids: List[Quote]
    asks: List[Quote]
    tick: float = 0.05

    @property
    def midpoint(self) -> float:
        a, b = self.bids[0].price, self.asks[0].price
        mp = abs(b - a) / 2
        tck = tick(min(a, b) + mp, 0.15)
        return round(tick(min(a, b) + mp, tick_size=self.tick), 2)

    def bid(self, n: int = 0) -> float:
        """
        Get the bid price at the specified depth
        """
        return self.bids[n].price

    def ask(self, n: int = 0) -> float:
        """
        Get the ask price at the specified depth
        """
        return self.asks[n].price

    def sort(self) -> None:
        """
        Sort asks and bids based on price
        sorting is done in place replacing asks and bids
        """
        self.bids.sort(key=lambda x: x.price, reverse=True)
        self.asks.sort(key=lambda x: x.price)
