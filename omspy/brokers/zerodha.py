import pyotp
from omspy.base import Broker, pre, post
from typing import Optional, List, Dict
from copy import deepcopy
from time import sleep
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from toolkit.webdriver import MyWebDriver
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
        tokpath="token.tok",
        exchange="NSE",
        product="MIS",
        totp=None,
    ):
        self._api_key = api_key
        self._secret = secret
        self._user_id = user_id
        self._password = password
        self._totp = totp
        self.exchange = exchange
        self.product = product
        self._store_access_token = True
        self._tokpath = tokpath
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
            with open(self._tokpath) as f:
                access_token = f.read()
                print(f"access token is {access_token}")
            self.kite.set_access_token(access_token)
            self.profile
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )
            self._shortcuts()
        except TokenException:
            print("Into Exception")
            self._login()
            self._shortcuts()
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )
        except Exception as e:
            print(f"Unknown Exception {e}")
            self._login()
            self._shortcuts()
            self.ticker = KiteTicker(
                api_key=self._api_key, access_token=self.kite.access_token
            )

    def _login(self) -> None:
        try:
            waitime = 45
            self.kite = KiteConnect(api_key=self._api_key)
            """
            options = Options()
            options.add_argument("--headless")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            """
            print("INIT DRIVER")
            driver = MyWebDriver().get_driver()
            driver.get(self.kite.login_url())
            print(f"success in DRIVER {driver}")
            print("GETTING LOGIN FORM")
            login_form = WebDriverWait(driver, waitime).until(
                EC.presence_of_element_located((By.CLASS_NAME, "login-form"))
            )
            login_form.find_elements(By.TAG_NAME, "input")[
                0].send_keys(self._user_id)
            login_form.find_elements(By.TAG_NAME, "input")[
                1].send_keys(self._password)
            WebDriverWait(driver, waitime).until(
                EC.presence_of_element_located((By.CLASS_NAME, "button-orange")))
            driver.find_element(By.XPATH, '//button[@type="submit"]').click()

            print(f"GETTING OTP {self._totp}")
            otp = pyotp.TOTP(self._totp).now()
            twofa_pass = f"{int(otp):06d}"
            print(f'twofa_pass is {twofa_pass}')
            twofa_form = WebDriverWait(driver, waitime).until(
                EC.presence_of_element_located((By.CLASS_NAME, "twofa-form")))
            twofa_form.find_elements(By.TAG_NAME, "input")[
                0].send_keys(twofa_pass)
            WebDriverWait(driver, waitime).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "button-orange"))
            )
            driver.find_element(By.XPATH, '//button[@type="submit"]').click()
            sleep(5)
            token = get_key(driver.current_url)
            print(f" {driver.current_url} is the current url")
            print(f" request token is {token}")
            access = self.kite.generate_session(
                request_token=token, api_secret=self._secret
            )
            print(f" session is {access}")
            self.kite.set_access_token(access["access_token"])
            with open(self._tokpath, "w") as f:
                f.write(access["access_token"])
            driver.close()
        except Exception as e:
            print(f"error {e} while authenticating omspy")
        else:
            return True

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
            variety="regular", validity="DAY",
        )
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

    def margins(self):
        return self.kite.margins()

    def ltp(self, exchsym):
        return self.kite.ltp(exchsym)


