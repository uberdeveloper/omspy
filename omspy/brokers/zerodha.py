import pyotp
from omspy.base import Broker, pre, post
from typing import Optional, List, Dict
from copy import deepcopy
import logging
import nodriver as uc
import time

connect = uc.Connection
connect._prepare_headless

from kiteconnect import KiteConnect
from kiteconnect import KiteTicker

from kiteconnect.exceptions import (
    TokenException,
    NetworkException,
    GeneralException,
    KiteException,
    InputException,
)


def get_key(url, key="request_token") -> Optional[str]:
    """
    Get the required key from the query parameter
    """
    from urllib.parse import parse_qs, urlparse

    req = urlparse(url)
    key = parse_qs(req.query).get(key)
    if key is None:
        return None
    else:
        return key[0]


class Zerodha(Broker):
    """
    Automated Trading class
    """

    def __init__(
        self,
        api_key,
        secret,
        user_id,
        password,
        PIN,
        exchange="NSE",
        product="MIS",
        totp=None,
        is_pin=False,
    ):
        self._api_key = api_key
        self._secret = secret
        self._user_id = user_id
        self._password = password
        self._pin = PIN
        self._totp = totp
        self.is_pin = is_pin
        self.exchange = exchange
        self.product = product
        self._store_access_token = True
        super(Zerodha, self).__init__()

    def _shortcuts(self) -> None:
        """
        Provides shortcuts to kite functions by mapping functions.
        Instead of calling at.kite.quote, you would directly call
        at.quote
        Note
        -----
        1) Kite functions are initialized only after authentication
        1) Not all functions are supported
        """
        self.margins = self.kite.margins
        self.ltp = self.kite.ltp
        self.quote = self.kite.quote
        self.ohlc = self.kite.ohlc
        self.holdings = self.kite.holdings

    def authenticate(self) -> None:
        """
        Authenticates a kite session if access token is already available
        Looks up token in token.tok file
        Useful for reconnecting instead of logging in again
        """
        try:
            self.kite = KiteConnect(api_key=self._api_key)
            with open("token.tok") as f:
                access_token = f.read()
            self.kite.set_access_token(access_token)
            self.profile
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )
            self._shortcuts()
        except TokenException:
            logging.error("Into Exception")
            self._login()
            self._shortcuts()
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )
        except:
            logging.error("Unknown Exception")
            self._login()
            self._shortcuts()
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )

    async def _async_login(self) -> None:
        self.kite = KiteConnect(api_key=self._api_key)
        browser = await uc.start(headless=True)
        url = self.kite.login_url()
        page = await browser.get(url)
        await page.get_content()
        user_id = await page.select('input[id="userid"]')
        await user_id.send_keys(self._user_id)
        password = await page.select('input[id="password"]')
        await password.send_keys(self._password)
        button = await page.select('button[type="submit"]')
        await button.click()
        time.sleep(2)
        twofa_pass = pyotp.TOTP(self._totp).now()
        twofa = await page.select('input[id="userid"]')
        await twofa.send_keys(twofa_pass)
        button = await page.select('button[type="submit"]')
        await button.click()
        time.sleep(2)
        await page.get_content()
        current_url = await page.evaluate("window.location.href")
        token = get_key(current_url)
        access = self.kite.generate_session(
            request_token=token, api_secret=self._secret
        )
        self.kite.set_access_token(access["access_token"])
        with open("token.tok", "w") as f:
            f.write(access["access_token"])
        time.sleep(1)
        browser.stop()

    def _login(self) -> None:
        uc.loop().run_until_complete(self._async_login())

    @property
    @post
    def orders(self) -> List[Dict]:
        status_map = {
            "OPEN": "PENDING",
            "COMPLETE": "COMPLETE",
            "CANCELLED": "CANCELED",
            "CANCELLED AMO": "CANCELED",
            "REJECTED": "REJECTED",
            "MODIFY_PENDING": "PENDING",
            "OPEN_PENDING": "PENDING",
            "CANCEL_PENDING": "PENDING",
            "AMO_REQ_RECEIVED": "PENDING",
            "TRIGGER_PENDING": "PENDING",
        }
        orderbook = self.kite.orders()
        orderbook = deepcopy(orderbook)
        if orderbook:
            for order in orderbook:
                order["status"] = status_map.get(order["status"])
            return orderbook
        else:
            return [{}]

    @property
    @post
    def positions(self) -> List[Dict]:
        """
        Return only the positions for the day
        """
        position_book = self.kite.positions().get("day")
        position_book = deepcopy(position_book)
        if position_book:
            for position in position_book:
                if position["quantity"] > 0:
                    position["side"] = "BUY"
                else:
                    position["side"] = "SELL"
            return position_book
        else:
            return [{}]

    @property
    @post
    def trades(self) -> List[Dict]:
        """
        Return all the trades
        """
        tradebook = self.kite.trades()
        if tradebook:
            return tradebook
        else:
            return [{}]

    @pre
    def order_place(self, **kwargs) -> Dict:
        """
        Place an order
        """
        order_args = dict(
            variety="regular", product="MIS", validity="DAY", exchange="NSE"
        )
        if kwargs.get("transaction_type"):
            kwargs["transaction_type"] = str(kwargs["transaction_type"]).upper()
        order_args.update(kwargs)
        return self.kite.place_order(**order_args)

    def order_cancel(self, **kwargs) -> Dict:
        """
        Cancel an existing order
        """
        order_id = kwargs.pop("order_id", None)
        order_args = dict(variety="regular")
        order_args.update(kwargs)
        if not (order_id):
            return {"error": "No order_id"}
        else:
            return self.kite.cancel_order(order_id=order_id, **order_args)

    def order_modify(self, **kwargs) -> Dict:
        """
        Modify an existing order
        Note
        ----
        All changes must be passed as keyword arguments
        """
        order_id = kwargs.pop("order_id", None)
        order_args = dict(variety="regular")
        order_args.update(kwargs)
        if not (order_id):
            return {"error": "No order_id"}
        else:
            return self.kite.modify_order(order_id=order_id, **order_args)

    @property
    def profile(self):
        return self.kite.profile()
