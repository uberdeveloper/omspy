from omspy.models import Quote
from omspy.utils import tick
from typing import List
from pydantic import BaseModel


class MarketDepth(BaseModel):
    bids: List[Quote]
    asks: List[Quote]
    tick: float = 0.05

    @property
    def midpoint(self):
        a, b = self.bids[0].price, self.asks[0].price
        mp = abs(b - a) / 2
        tck = tick(min(a, b) + mp, 0.15)
        return round(tick(min(a, b) + mp, tick_size=self.tick), 2)
