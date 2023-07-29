from omspy.base import Broker, post, pre
from typing import Optional, List, Dict, Union
from neo_api_client import NeoAPI
import pendulum
import logging


class Neo(Broker):
    """
    Automated trading class for Neo Broker
    """

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        user_id: str,
        password: str,
        twofa: str,
        **kwargs,
    ):
        self._user_id = user_id
        self._password = password
        self._consumer_key = consumer_key
        self._consumer_secret = consumer_secret
        self._mpin = twofa
        self._kwargs = kwargs
        super(Neo, self).__init__()

    def authenticate(self) -> Dict:
        mobilenumber = self._kwargs.pop("mobilenumber", None)
        pan = self._kwargs.pop("pan", None)
        client = NeoAPI(
            consumer_key=self._consumer_key,
            consumer_secret=self._consumer_secret,
            **self._kwargs,
        )
        self.neo = client
        client.login(
            password=self._password,
            userid=self._user_id,
            mobilenumber=mobilenumber,
            pan=pan,
            mpin=self._mpin,
        )
        return client.session_2fa(self._mpin)

    @pre
    def order_place(self, **kwargs) -> Union[str, None]:
        """
        place an order
        """
        try:
            order_args = dict(
                exchange_segment="NSE",
                product="MIS",
                order_type="MKT",
                validity="DAY",
            )
            order_args["transaction_type"] = kwargs.pop("transaction_type").upper()[0]
            for key in ("quantity", "price", "trigger_price", "disclosed_quantity"):
                val = str(kwargs.pop(key, 0))
                order_args.update({key: val})
            order_args.update(kwargs)
            response = self.neo.place_order(**order_args)
            return response.get("nOrdNo")
        except Exception as e:
            logging.error(e)
            return None
