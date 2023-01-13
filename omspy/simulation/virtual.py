import random
from typing import Optional
from omspy.models import OrderBook, Quote


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
        b = Quote(
            price=bid - i * tick,
            quantity=random.randrange(q1, q2),
            orders_count=random.randrange(5, 15),
        )
        a = Quote(
            price=bid + i * tick,
            quantity=random.randrange(q1, q2),
            orders_count=random.randrange(5, 15),
        )
        bids.append(b)
        asks.append(a)
    return OrderBook(ask=asks, bid=bids)
