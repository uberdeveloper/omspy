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
        super(Icici, self).__init__()

    def authenticate(self):
        self.breeze = BreezeConnect(self._api_key)
        self.breeze.generate_session(
            api_secret=self._secret, session_token=self._session_token
        )

    def profile(self):
        details = self.breeze.get_customer_details(api_session=self._session_token)
        return details

    @pre
    def order_place(self, **kwargs)->dict:
        """
        Place an order
        """
        symbol = kwargs.pop("stock_code")
        order_type = kwargs.pop("order_type", "MARKET")
        if "stop" in order_type.lower():
            order_type = "stoploss"
        elif "sl" in order_type.lower():
            order_type = "stoploss"

        name = self.breeze.get_names(exchange_code="NSE", stock_code=symbol)
        order_args = dict(
                validity="day",
                product="margin",
                stock_code=name['isec_stock_code'],
                exchange_code="NSE",
                order_type=order_type,
                )
        order_args.update(kwargs)
        return self.breeze.place_order(**order_args)

    @pre
    def order_modify(self, order_id:str, **kwargs)->dict:
        """
        Modify an existing order
        """
        if "price" in kwargs:
            order_type = "LIMIT"
        elif "stoploss" in kwargs:
            order_type = "stoploss"
        else:
            order_type ="LIMIT"
        order_args = dict(
                validity="day",
                exchange_code="NSE",
                order_id=order_id,
                order_type=order_type,
                )
        order_args.update(kwargs)
        return self.breeze.modify_order(**order_args)


    def order_cancel(self, order_id:str, **kwargs)->dict:
        """
        Cancel an existing order
        """
        order_args = dict(
                exchange_code="NSE",
                )
        order_args.update(kwargs)
        return self.breeze.cancel_order(order_id=order_id, **order_args)
