import pyotp
from omspy.base import Broker, pre, post
from typing import Optional, List, Dict
from copy import deepcopy
import logging
import nodriver as uc
import time
from breeze_connect import BreezeConnect


class Icici(Broker):
    def __init__(
        self,
        api_key,
        secret,
        user_id,
        password,
        PIN,
        totp: Optional[str] = None,
        session_token: Optional[int] = None,
        **kwargs
    ):
        self.base_url = "https://api.icicidirect.com/apiuser/"
        self._api_key = api_key
        self._secret = secret
        self._user_id = user_id
        self._password = password
        self._pin = PIN
        self._totp = totp
        self._session_token = session_token
        self._store_access_token = True
        super(Icici).__init__(**kwargs)

    def authenticate(self):
        self.breeze = BreezeConnect(self._api_key)
        self.breeze.generate_session(
            api_secret=self._secret, session_token=self._session_token
        )

    def profile(self):
        details = self.breeze.get_customer_details(api_session=self._session_token)
        return details
