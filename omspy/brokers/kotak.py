from omspy.base import Broker,pre,post
from typing import Optional,List,Dict
from ks_api_client import ks_api


class Kotak(Broker):
    """
    Automated Trading class
    """

    def __init__(self,access_token:str,userid:str,
            password:str,consumer_key:str,
            access_code:Optional[str]=None, ip:str="127.0.0.1",
            app_id:str="default"):
        pass

    def get_instrument_token(self, **kwargs)->int:
        pass

    def authenticate(self)->None:
        pass

    def orders(self) -> List[Dict]:
        pass

    def positions(self)->List[Dict]:
        pass

    def trades(self) -> List[Dict]:
        pass

    def order_place(self, **kwargs) -> Dict:
        pass

    def order_cancel(self, **kwargs) -> Dict:
        pass

    def order_modify(self, **kwargs) -> Dict:
        pass
