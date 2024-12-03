from omspy.base import Broker, pre, post
from typing import Optional, List, Dict, Union, Set
import pendulum
import pyotp
import logging
from NorenRestApiPy.NorenApi import NorenApi


class BaseNoren(NorenApi):
    def __init__(self, host: str, websocket: str):
        super(BaseNoren, self).__init__(host=host, websocket=websocket)


class Noren:
    def __init__(
        self,
        user_id: str,
        password: str,
        totp: str,
        vendor_code: str,
        app_key: str,
        imei: str,
        *args,
        **kwargs
    ):
        self._user_id = user_id
        self._password = password
        self._totp = totp
        self._vendor_code = vendor_code
        self._app_key = app_key
        self._imei = imei
        self._host = kwargs.get("host", "https://star.prostocks.com/NorenWClientTP")
        self._websocket = kwargs.get("websocket", "wss://star.prostocks.com/NorenWS/")
        self.noren = None

    @property
    def attribs_to_copy_modify(self) -> set:
        return {"symbol", "exchange"}

    def login(self):
        return self.noren.login(
            userid=self._user_id,
            password=self._password,
            twoFA=pyotp.TOTP(self._totp).now(),
            vendor_code=self._vendor_code,
            api_secret=self._app_key,
            imei=self._imei,
        )

    def authenticate(self) -> Union[Dict, None]:
        self.noren = BaseNoren(self._host, self._websocket)
        return self.login()
