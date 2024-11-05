import pyotp
from omspy.base import Broker, pre, post
from typing import Optional, List, Dict
from copy import deepcopy
import logging
import nodriver as uc
import time
from breeze_connect import BreezeConnect
import pendulum
from omspy.utils import tick
from urllib.parse import quote_plus, parse_qs, urlparse


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
        **kwargs,
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

    async def _async_login(self):
        url = f"https://api.icicidirect.com/apiuser/login?api_key={quote_plus(self._api_key)}"
        browser = await uc.start(headless=True)
        page = await browser.get(url)
        await page.get_content()
        user_id = await page.select('input[id="txtuid"]')
        await user_id.send_keys(str(self._user_id))
        password = await page.select('input[id="txtPass"]')
        await password.send_keys(str(self._password))
        accept = await page.select('input[id="chkssTnc"]')
        await accept.click()

        button = await page.select('input[type="button"]')
        await button.click()
        time.sleep(2)
        otp = pyotp.TOTP(self._totp).now()
        twofa = await page.select_all('input[inputmode="decimal"]')
        for n, ctrl in zip(str(otp), twofa):
            await ctrl.send_keys(n)
        button = await page.select('input[id="Button1"]')
        await button.click()
        time.sleep(2)
        await page.get_content()
        current_url = await page.evaluate("window.location.href")
        time.sleep(2)
        parsed_args = parse_qs(urlparse(current_url).query)
        if "apisession" in parsed_args:
            self._session_token = int(parsed_args["apisession"][0])
            with open("icici_session_token.txt", "w") as f:
                f.write(str(self._session_token))
        browser.stop()

    def _login(self):
        uc.loop().run_until_complete(self._async_login())

    def _login_with_token_file(self, token_filename: Optional[str] = None):
        if token_filename is None:
            token_filename = "icici_session_token.txt"
        with open(token_filename, "r") as f:
            self._session_token = int(f.read())
        self.breeze.generate_session(
            api_secret=self._secret, session_token=self._session_token
        )

    def authenticate(self):
        self.breeze = BreezeConnect(self._api_key)
        if not self._session_token:
            try:
                self._login_with_token_file()
            except Exception as e:
                logging.error(e)
                logging.info("Trying a fresh login")
                self._login()
                self.breeze.generate_session(
                    api_secret=self._secret, session_token=self._session_token
                )
        else:
            self.breeze.generate_session(
                api_secret=self._secret, session_token=self._session_token
            )

    def profile(self):
        details = self.breeze.get_customer_details(api_session=self._session_token)
        return details

    def _get_order_type(self, **kwargs) -> str:
        """
        get order type based on the keyword arguments
        """
        order_type = kwargs.pop("order_type", "MARKET")
        if "price" in kwargs:
            if kwargs["price"] == 0:
                return "MARKET"
            else:
                return "LIMIT"
        elif "stoploss" in kwargs:
            return "LIMIT"
        elif "stop" in order_type.lower():
            return "LIMIT"
        elif "sl" in order_type.lower():
            return "LIMIT"
        return order_type

    def _get_price_args(self, order_type: str, **kwargs) -> Dict:
        """
        return price arguments based on order type
        and kwargs
        """
        order_type = str(order_type).upper()
        side = str(kwargs.get("action")).lower()
        if order_type == "LIMIT":
            price = kwargs["price"]
            tick_size = 0.01 if price < 100 else 0.05
            return dict(price=price, stoploss=0)
        elif order_type == "SL-M":
            stoploss = kwargs["stoploss"]
            tick_size = 0.01 if stoploss < 100 else 0.05
            if side == "buy":
                price = tick(stoploss * 1.01, tick_size)
                return dict(price=price, stoploss=stoploss)
            else:
                price = tick(stoploss * 0.99, tick_size)
                return dict(price=price, stoploss=stoploss)
        elif order_type == "SL":
            price = kwargs["price"]
            return dict(price=price, stoploss=0)
        else:
            return dict(price=0, stoploss=0)

    @pre
    def order_place(self, **kwargs) -> Optional[str]:
        """
        Place an order
        """
        symbol = kwargs.pop("stock_code")
        order_type = kwargs.pop("order_type", self._get_order_type(**kwargs))
        price_args = self._get_price_args(order_type, **kwargs)
        if "sl" in order_type.lower() or "stop" in order_type.lower():
            order_type = "LIMIT"
        name = self.breeze.get_names(exchange_code="NSE", stock_code=symbol)
        order_args = dict(
            validity="day",
            product="margin",
            stock_code=name["isec_stock_code"],
            exchange_code="NSE",
            order_type=order_type,
        )
        order_args.update(kwargs)
        order_args.update(price_args)
        response = self.breeze.place_order(**order_args)
        success = response["Success"]
        if success and "order_id" in success:
            return success["order_id"]
        else:
            return None

    @pre
    def order_modify(self, order_id: str, **kwargs) -> Optional[str]:
        """
        Modify an existing order
        """
        order_type = self._get_order_type(**kwargs)
        order_args = dict(
            validity="day",
            exchange_code="NSE",
            order_id=order_id,
            order_type=order_type,
        )
        order_args.update(kwargs)
        response = self.breeze.modify_order(**order_args)
        success = response["Success"]
        if success and "order_id" in success:
            return success["order_id"]
        else:
            return None

    def order_cancel(self, order_id: str, **kwargs) -> Optional[str]:
        """
        Cancel an existing order
        """
        order_args = dict(
            exchange_code="NSE",
        )
        order_args.update(kwargs)
        response = self.breeze.cancel_order(order_id=order_id, **order_args)
        success = response["Success"]
        if success and "order_id" in success:
            return success["order_id"]
        else:
            return None

    @property
    @post
    def orders(self) -> List[Optional[Dict]]:
        """
        Return all the orders
        """
        tz = "Asia/Kolkata"
        from_date = str(pendulum.today(tz))
        to_date = str(pendulum.now(tz))
        response = self.breeze.get_order_list(
            exchange_code="NSE", from_date=from_date, to_date=to_date
        )
        success = response["Success"]
        if isinstance(success, list):
            orderbook = success
        else:
            orderbook = []
        status_map = {
            "EXECUTED": "COMPLETE",
            "ORDERED": "PENDING",
            "CANCELLED": "CANCELED",
            "REJECTED": "CANCELED",
        }
        if len(orderbook) > 0:
            for order in orderbook:
                status = str(order["status"]).upper()
                order["status"] = status_map.get(status, "PENDING")
                order["filled_quantity"] = (
                    int(order["quantity"])
                    - int(order["pending_quantity"])
                    - int(order["cancelled_quantity"])
                )
                order["action"] = order["action"].upper()
        return orderbook

    @property
    @post
    def positions(self) -> List[Optional[Dict]]:
        """
        Return all the positions
        """
        response = self.breeze.get_portfolio_positions()
        success = response["Success"]
        if isinstance(success, list):
            positions = success
        else:
            positions = []
        return positions

    @property
    @post
    def trades(self) -> List[Optional[Dict]]:
        """
        Return all the trades
        """
        tz = "Asia/Kolkata"
        from_date = str(pendulum.today(tz))
        to_date = str(pendulum.now(tz))
        response = self.breeze.get_trade_list(
            exchange_code="NSE", from_date=from_date, to_date=to_date
        )
        success = response["Success"]
        if isinstance(success, list):
            tradebook = success
        else:
            tradebook = []
        return tradebook
