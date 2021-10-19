from omspy.base import Broker, pre, post


class Paper(Broker):
    """
    An empty broker class
    """

    def __init__(self, orders=None, trades=None, positions=None):
        """
        Initialize the paper trader with some dummy data to return
        orders
            list of orders
        trades
            list of trades
        positions
            list of positions
        """
        self.__orders = orders
        self.__trades = trades
        self.__positions = positions
        super(Paper, self).__init__()

    def authenticate(self):
        return True

    @property
    @post
    def orders(self):
        return self.__orders if self.__orders else [{}]

    @property
    @post
    def trades(self):
        return self.__trades if self.__trades else [{}]

    @property
    @post
    def positions(self):
        return self.__positions if self.__positions else [{}]

    @pre
    def order_place(self, **kwargs):
        return kwargs

    @pre
    def order_modify(self, order_id: str, **kwargs):
        return kwargs

    @pre
    def order_cancel(self, order_id: str):
        pass
