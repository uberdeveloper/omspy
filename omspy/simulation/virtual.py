import random
from typing import Optional
from omspy.models import OrderBook, Quote
from pydantic import BaseModel, PrivateAttr
from enum import Enum


class TickerMode(Enum):
    RANDOM = 1
    MANUAL = 2


def generate_price(start: int = 100, end: int = 110) -> int:
    """
    Generate a random price in the given range between start and end
    start
        starting value
    end
        ending value
    Note
    ----
    1) If the start value is greater than end value, the values are swapped
    """
    if start > end:
        start, end = end, start
    return random.randrange(start, end)


def generate_orderbook(
    bid: float = 100.0,
    ask: float = 100.05,
    depth: int = 5,
    tick: float = 0.01,
    quantity: int = 100,
) -> OrderBook:
    """
    generate a fake orderbook
    bid
        bid price
    ask
        ask price
    depth
        depth of the orderbook
    tick
        difference in price between orders
    quantity
        average quantity of orders per price quote

    Note
    ----
    1) orderbook is generated with a uniform tick difference between subsequent quotes
    2) quantity is averaged between value quantity/2 and quantity * 1.5 using randrange function
    3) num of orders is randomly picked between 5 to 15
    4) if bid price is greater than ask, the values are swapped
    """
    if bid > ask:
        bid, ask = ask, bid
    asks = []
    bids = []
    q1, q2 = int(quantity * 0.5), int(quantity * 1.5)
    for i in range(depth):
        bid_qty = random.randrange(q1, q2)
        ask_qty = random.randrange(q1, q2)
        b = Quote(
            price=bid - i * tick,
            quantity=bid_qty,
            orders_count=min(random.randrange(5, 15), bid_qty),
        )
        a = Quote(
            price=ask + i * tick,
            quantity=ask_qty,
            orders_count=min(random.randrange(5, 15), ask_qty),
        )
        bids.append(b)
        asks.append(a)
    return OrderBook(ask=asks, bid=bids)


class Ticker(BaseModel):
    """
    A simple ticker class to generate fake data
    name
        name for this ticker
    token
        a unique instrument token
    initial_price
        initial_price for the ticker
    ticker_mode
        ticker mode; random or otherwise
    Note
    -----
    1) If ticker mode is random, price is generated based on random walk from normal distribution
    """

    name: str
    token: Optional[int] = None
    initial_price: float = 100
    mode: TickerMode = TickerMode.RANDOM

    @property
    def is_random(self) -> bool:
        """
        returns True if the mode is random else False
        """
        return True if self.mode == TickerMode.RANDOM else False
