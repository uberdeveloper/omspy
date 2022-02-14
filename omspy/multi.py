"""
Module for multi-user multi-broker implementation
"""
from pydantic import BaseModel
from omspy.base import Broker
from typing import Dict,List,Optional


class User(BaseModel):
    """
    A basic user class for multi user environment
    """
    broker:Broker
    scale:float = 1.0
    name:Optional[str]
    exclude:Optional[Dict]

    class Config:
        underscore_attrs_are_private = True
        arbitrary_types_allowed = True
        

class MultiBroker:
    """
    Multi-broker implementation
    """
    def __init__(self,users:List[User]):
        self._users:List[User] = users

    def add(self, user:User):
        """
        Add a user
        """
        self._users.append(user)

    @property
    def users(self)->List[User]:
        return self._users

    @property
    def count(self)->int:
        return len(self.users)

    def _call(self, method, **kwargs):
        """
        Call the given method on all the users
        """
        pass
