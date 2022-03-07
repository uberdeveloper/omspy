"""
Module for multi-user multi-broker implementation
"""
from pydantic import BaseModel
from omspy.base import Broker
from omspy.order import Order
from typing import Dict, List, Optional
from collections import defaultdict
import logging


class User(BaseModel):
    """
    A basic user class for multi user environment
    """

    broker: Broker
    scale: float = 1.0
    name: Optional[str]
    client_id: Optional[str]
    exclude: Optional[Dict]

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True


class MultiUser:
    """
    Multi-userimplementation
    """

    def __init__(self, users: List[User]):
        self._users: List[User] = users
        self._orders: defaultdict(list) = {}

    def add(self, user: User):
        """
        Add a user
        """
        self._users.append(user)

    @property
    def users(self) -> List[User]:
        return self._users

    @property
    def orders(self) -> Dict[str, Order]:
        return self._orders

    @property
    def count(self) -> int:
        return len(self.users)

    def _call(self, method, **kwargs):
        """
        Call the given method on all the users
        """
        pass

    def order_place(self, order: Order, **kwargs):
        """
        Place an order
        """
        self._orders[order.id] = []
        for user in self.users:
            order2 = order.clone()
            order2.quantity = int(user.scale * order.quantity)
            order2.parent_id = order2.pseudo_id = order.id
            self._orders[order.id].append(order2)
            order2.execute(user.broker, **kwargs)


class MultiOrder(Order):
    _orders: List[Order] = []

    @property
    def orders(self) -> List[Order]:
        return self._orders

    @property
    def count(self) -> int:
        """
        Return the number of orders
        """
        return len(self.orders)

    def create(self, users: Optional[MultiUser]) -> List[Order]:
        for user in users:
            order2 = self.clone()
            order2.quantity = int(user.scale * self.quantity)
            order2.pseudo_id = self.id
            self._orders.append(order2)
            order2.save_to_db()
        self.save_to_db()
        return self.orders

    def save_to_db(self) -> bool:
        """
        save or update the order to db
        """
        if self.connection:
            values = []
            values.append(self.dict(exclude=self._exclude_fields))
            for order in self.orders:
                values.append(order.dict(exclude=self._exclude_fields))
            self.connection["orders"].upsert_all(values, pk="id")
            return True
        else:
            logging.info("No valid database connection")
            return False
