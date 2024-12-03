from omspy.base import Broker, pre, post
from typing import Optional, List, Dict, Union, Set
import pendulum
import pyotp
import logging
from NorenRestApiPy.NorenApi import NorenApi


class BaseNoren(NorenApi):
    def __init__(self, host: str, websocket: str):
        super(BaseNoren, self).__init__(host=host, websocket=websocket)


class Noren(BaseNoren):
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
        super(Noren, self).__init__(*args, **kwargs)
