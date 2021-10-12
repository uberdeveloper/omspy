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
        if orders:
            self.__orders = orders
        if trades:
            self.__trades = trades
        if positions:
            self.__positions = positions
        super(Paper, self).__init__()

    @post
    @property
    def orders(self):
        return self.__orders if self.__orders else [{}]

    @post
    @property
    def trades(self):
        return self.__trades if self.__trades else [{}]

    @post
    @property
    def positions(self):
        return self.__positions if self.__positions else [{}]

    @pre
    def order_place(self, **kwargs):
        pass

    @pre
    def order_modify(self, **kwargs):
        pass

    @pre
    def order_cancel(self, **kwargs):
        pass
