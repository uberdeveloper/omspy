from omspy.brokers.api_helper import ShoonyaApiPy
from omspy.base import Broker, pre, post
from typing import Optional, List, Dict, Union
import pendulum


class Finvasia(Broker):
    """
    Automated Trading class
    """

    def __init__(self, user_id:str, password:str, pin:str, vendor_code:str, app_key: str, imei:str):
        self._user_id = user_id
        self._password = password
        self._pin = pin
        self._vendor_code = vendor_code
        self._app_key = app_key
        self._imei = imei
        self.finvasia = ShoonyaApiPy()


    def login(self):
        pass

    @property
    @post
    def orders(self)->List[Dict]:
        pass


    @property
    @post
    def positions(self)->List[Dict]:
        pass


    def trades(self)->List[Dict]:
        pass

    def order_place(self, symbol:str, side:str, exchange:str='NSE', quantity:int=1, **kwargs)->Union[str,None]:
        pass

    def order_cancel(self, order_id:str)->Dict:
        pass

    def order_modify(self, order_id:str, **kwargs)->Union[str,None]:
        pass


