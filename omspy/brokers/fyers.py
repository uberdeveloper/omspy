from omspy.base import Broker, pre, post
from typing import Optional, List, Dict
from urllib.parse import urlparse, parse_qs
from fyers_api import fyersModel, accessToken
from copy import deepcopy

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Constant dictionaries
EXCHANGES = {10: "NSE", 11: "MCX", 12: "BSE"}
SEGMENTS = {10: "capital", 11: "equity", 12: "currency", 20: "commodity"}
ORDER_TYPES = {1: "LIMIT", 2: "MARKET", 3: "SL-M", 4: "SL"}
STATUS = {1: "CANCELED", 2: "COMPLETE", 4: "PENDING", 5: "REJECTED", 6: "PENDING"}
SIDES = {1: "buy", -1: "sell"}


def get_key(url, key="request_token") -> Optional[str]:
    """
    Get the required key from the query parameter
    """
    req = urlparse(url)
    key = parse_qs(req.query).get(key)
    if key is None:
        return None
    else:
        return key[0]


class Fyers(Broker):
    def __init__(self, app_id, secret, user_id, password, pan, log_path="."):
        self._app_id = app_id
        self._secret = secret
        self._user_id = user_id
        self._password = password
        self._pan = pan
        self._store_access_token = True
        self._log_path = log_path
        super(Fyers, self).__init__()

    def authenticate(self) -> None:

        """
        Authenticates a fyers session if access token is already available
        Looks up token in fyers_token.tok file
        Useful for reconnecting instead of logging in again
        """
        try:
            with open("fyers_token.tok") as f:
                access_token = f.read()
            self.fyers = fyersModel.FyersModel(
                client_id=self._app_id, token=access_token, log_path=self._log_path
            )
            self.quote = self.fyers.quotes
        except:
            print("Unknown Exception")
            self._login()

    def _login(self) -> None:
        session = accessToken.SessionModel(
            client_id=self._app_id,
            secret_key=self._secret,
            redirect_uri="http://127.0.0.1",
            response_type="code",
            grant_type="authorization_code",
            state="private",
        )
        auth_url = session.generate_authcode()
        options = webdriver.ChromeOptions()
        options.add_argument("--disable-notifications")
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        driver.get(auth_url)
        driver.find_element_by_id("fyers_id").send_keys(self._user_id)
        driver.find_element_by_id("password").send_keys(self._password)
        driver.find_element_by_id("pancard").send_keys(self._pan)

        driver.find_element_by_xpath("//button[@id='btn_id']").click()
        WebDriverWait(driver, 20).until((EC.url_changes(driver.current_url)))

        parsed = urlparse(driver.current_url)
        auth_code = parse_qs(parsed.query)["auth_code"][0]
        session.set_token(auth_code)
        response = session.generate_token()
        token = response["access_token"]
        with open("fyers_token.tok", "w") as f:
            f.write(token)
        self.fyers = fyersModel.FyersModel(client_id=self._app_id, token=token)
        self.quote = self.fyers.quotes
        driver.close()

    @property
    def profile(self) -> Dict:
        return self.fyers.get_profile()

    @property
    def funds(self) -> Dict:
        return self.fyers.funds()

    @property
    @post
    def orders(self) -> List[Dict]:
        orderbook = self.fyers.orderbook().get("orderBook")
        orderbook = deepcopy(orderbook)
        if orderbook:
            for order in orderbook:
                order["exchange"] = EXCHANGES.get(order["exchange"])
                order["segment"] = SEGMENTS.get(order["segment"])
                order["side"] = SIDES.get(order["side"])
                order["status"] = STATUS.get(order["status"])
                order["type"] = ORDER_TYPES.get(order["type"])

            return orderbook
        else:
            return [{}]

    @property
    @post
    def positions(self) -> List[Dict]:
        position_book = self.fyers.positions().get("netPositions")
        position_book = deepcopy(position_book)
        if position_book:
            for position in position_book:
                position["side"] = SIDES.get(position["side"])
            return position_book
        else:
            return [{}]

    @property
    @post
    def trades(self) -> List[Dict]:
        tradebook = self.fyers.tradebook().get("tradeBook")
        tradebook = deepcopy(tradebook)
        if tradebook:
            for trade in tradebook:
                trade["side"] = SIDES.get(trade["side"])
                trade["exchange"] = EXCHANGES.get(trade["exchange"])
                trade["segment"] = SEGMENTS.get(trade["segment"])
            return tradebook
        else:
            return [{}]

    @pre
    def order_place(
        self,
        symbol: str,
        side: str,
        quantity: int = 1,
        order_type: str = "MARKET",
        **kwargs
    ) -> Dict:
        """
        Place an actual order with broker
        """
        # Reverse look up maps
        rev_sides = {v: k for k, v in SIDES.items()}
        rev_order_types = {v: k for k, v in ORDER_TYPES.items()}
        side = rev_sides.get(side.lower())
        order_type = kwargs.pop("type", "market").upper()
        order_type = rev_order_types.get(order_type)
        if "qty" not in kwargs:
            kwargs["qty"] = 1
        order_args = {"side": side, "type": order_type, "symbol": symbol}
        for k, v in kwargs.items():
            if k not in order_args:
                order_args[k] = v
        response = self.fyers.place_order(order_args)
        return response

    @pre
    def order_modify(self, **kwargs) -> Dict:
        """
        Modify an actual order with the broker
        """
        # Reverse look up map
        rev_order_types = {v: k for k, v in ORDER_TYPES.items()}
        if kwargs.get("type"):
            order_type = kwargs.get("type", "market").upper()
            order_type = rev_order_types.get(order_type)
            kwargs.update({"type": order_type})
        response = self.fyers.modify_order(kwargs)
        return response

    def order_cancel(self, order_id: str) -> Dict:
        """
        Cancel an actual order with the broker
        """
        response = self.fyers.cancel_order({"id": order_id})
        return response
