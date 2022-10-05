import os
import random
import requests
from omspy.base import Broker, pre, post
from omspy.utils import dict_filter
from requests_oauthlib import OAuth2Session

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from typing import Dict, List
import pyotp


def get_authorization_url():
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    authorization_url, _state = oauth.authorization_url(
        authorization_base_url, access_type="authorization_code"
    )
    return authorization_url


def fetch_all_contracts(exchanges=["NSE", "NFO"]):
    """
    Fetch all contracts for the given list of exchanges
    exchanges
        exchanges as a list
    """
    url = "https://masterswift.mastertrust.co.in/api/v2/contracts.json?exchanges={exc}"
    # All contracts are stored as dictionary keys
    contracts = {}
    for e in exchanges:
        url2 = url.format(exc=e)
        req = requests.get(url2).json()
        for k, v in req.items():
            for c in v:
                symbol = c["trading_symbol"]
                code = c["code"]
                contracts[f"{e}:{symbol}"] = code
    return contracts


def get_instrument_token(contracts, exchange, symbol):
    """
    Fetch the instrument token
    contracts
        the contracts master as a dictionary
    exchange
        exchange to look up for
    symbol
        symbol to look up for
    """
    return contracts.get(f"{exchange}:{symbol}")


class MasterTrust(Broker):
    """
    Automated Trading class
    """

    def __init__(
        self,
        client_id,
        password,
        PIN,
        secret,
        exchange="NSE",
        product="MIS",
        token_file="token.tok",
    ):
        print("into here")
        self.filter = dict_filter
        self._client_id = client_id
        self._password = password
        self._pin = PIN
        self._secret = secret
        self.exchange = exchange
        self.product = product
        self._store_access_token = True
        self._access_token = None
        self.token_file = token_file
        self.base_url = "https://masterswift-beta.mastertrust.co.in"
        self.authorization_base_url = f"{self.base_url}/oauth2/auth"
        self.token_url = f"{self.base_url}/oauth2/token"
        super(MasterTrust, self).__init__()
        try:
            with open(self.token_file, "r") as f:
                access_token = f.read()
            self._access_token = access_token
        except Exception as e:
            print("Token not found", e)

        self._set_headers()
        self._sides = {"BUY": "SELL", "SELL": "BUY"}

    @property
    def headers(self):
        return self._headers

    @property
    def access_token(self):
        return self._access_token

    @property
    def client_id(self):
        return self._client_id

    def _set_headers(self):
        self._headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {self._access_token}",
            "Cache-Control": "no-cache",
        }

    def get_authorization_url(
        self, client_id="APIUSER", redirect_uri="http://127.0.0.1/", scope=["orders"]
    ):
        oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
        authorization_url, _state = oauth.authorization_url(
            self.authorization_base_url, access_type="authorization_code"
        )
        return authorization_url

    def get_access_token(self, url, redirect_uri="http://127.0.0.1/", scope=["orders"]):
        # to make oauth2 work with http
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
        oauth = OAuth2Session("APIUSER", redirect_uri=redirect_uri, scope=scope)
        token = oauth.fetch_token(
            self.token_url, authorization_response=url, client_secret=self._secret
        )
        access_token = token["access_token"]
        self._access_token = access_token
        with open(self.token_file, "w") as f:
            f.write(access_token)
        return access_token

    def _shortcuts(self):
        """
        Provides shortcuts to master trust function
        """
        pass

    def authenticate(self, force=False):
        """
        Authenticates a session if access token is already
        available by looking at the token.tok file.
        In case authentication fails, try a fresh login
        force
            Force an authentication even if tokens exists
        """
        try:
            if not (force):
                with open(self.token_file, "r") as f:
                    access_token = f.read()
                self._access_token = access_token
                self._set_headers()
            else:
                login_url = self._login()
                access_token = self.get_access_token(login_url)
                self._access_token = access_token
                self._set_headers()
        except Exception as e:
            print(e)
            login_url = self._login()
            access_token = self.get_access_token(login_url)
            self._access_token = access_token
            self._set_headers()

    def _login(self):
        import time

        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        driver = webdriver.Chrome(options=options)
        url = self.get_authorization_url()
        driver.get(url)
        time.sleep(2)
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-container"))
        )
        driver.find_element_by_name("login_id").send_keys(self._client_id)
        driver.find_element_by_name("password").send_keys(self._password)
        driver.find_element_by_xpath('//button[@type="submit"]').click()
        time.sleep(2)
        WebDriverWait(driver, 45).until(
            EC.presence_of_element_located((By.CLASS_NAME, "btn-container"))
        )
        driver.find_element_by_xpath('//input[@type="password"]').send_keys(
            pyotp.TOTP(self._pin).now()
        )
        driver.find_element_by_xpath('//button[@type="submit"]').click()
        time.sleep(2)
        current_url = driver.current_url
        driver.close()
        return current_url

    def _response(self, response, full=False):
        """
        response
            response is the raw response from broker
        full
            if True, the entire json response is returned
            useful for debugging purposes and getting extra information
        """
        try:
            resp = response.json()
            if full or (resp.get("status") == "error"):
                return resp
            else:
                return resp["data"]
        except:
            return {}

    def _get_instrument_token(self, symbol, exchange="NSE", contracts=None):
        if not (contracts):
            contracts = self.contracts
        return get_instrument_token(
            contracts=contracts, exchange=exchange, symbol=symbol
        )

    @property
    def profile(self):
        """
        Get the profile for the user
        """
        url = f"{self.base_url}/api/v1/user/profile"
        payload = {"client_id": self.client_id}
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp)

    @post
    def positions(self):
        """
        Return only the positions for the day
        """
        url = f"{self.base_url}/api/v1/positions"
        payload = {"client_id": self.client_id, "type": "live"}
        resp = requests.get(url, headers=self.headers, params=payload)
        resp = self._response(resp)
        for r in resp:
            r["side"] = "BUY" if r.get("quantity", 0) > 0 else "SELL"
        return resp

    @post
    def completed_orders(self):
        """
        Return the completed orders for the day
        """
        url = f"{self.base_url}/api/v1/orders"
        payload = {"client_id": self.client_id, "type": "completed"}
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp).get("orders", [])

    @post
    def pending_orders(self):
        """
        Return the completed orders for the day
        """
        url = f"{self.base_url}/api/v1/orders"
        payload = {"client_id": self.client_id, "type": "pending"}
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp).get("orders", [])

    def orders(self):
        """
        Return the entire orderbook for the day including
        completed and pending orders
        """
        pending = self.pending_orders()
        completed = self.completed_orders()
        pending.extend(completed)
        return pending

    def trades(self):
        """
        Return the tradebook for the day
        """
        url = f"{self.base_url}/api/v1/trades"
        payload = {"client_id": self.client_id}
        resp = requests.get(url, headers=self.headers, params=payload)
        return self._response(resp).get("trades", [])

    def realized_mtm(self, positions=None):
        """
        Get the realized MTM
        """
        if not (positions):
            positions = self.positions()
        if len(positions) > 0:
            return sum([float(p["realized_mtm"]) for p in positions])
        else:
            # Return 0 in case of no transactions
            return 0

    def unrealized_mtm(self, positions=None):
        """
        Get the unrealized MTM
        """
        if not (positions):
            positions = self.positions()
        if len(positions) == 0:
            collect = {p["symbol"]: 0 for p in positions}
        else:
            collect = {}
            for p in positions:
                if p["quantity"] > 0:
                    collect[p["symbol"]] = (
                        p["ltp"] - (-p["net_amount"] / p["quantity"])
                    ) * p["quantity"] - p["realized_mtm"]
                elif p["quantity"] < 0:
                    collect[p["symbol"]] = (
                        p["ltp"] - (-p["net_amount"] / p["quantity"])
                    ) * p["quantity"] - p["realized_mtm"]
                else:
                    collect[p["symbol"]] = 0
        return sum(list(collect.values()))

    def mtm(self, positions=None):
        """
        Get the mtm
        """
        if not (positions):
            positions = self.positions()
        realized_mtm = self.realized_mtm(positions=positions)
        unrealized_mtm = self.unrealized_mtm(positions=positions)
        return realized_mtm + unrealized_mtm

    def net_qty(self, symbol):
        """
        Get the net quantity
        """
        positions = self.positions()
        if symbol is None:
            return {p["symbol"]: p["quantity"] for p in positions}
        else:
            for p in positions:
                if p["symbol"] == symbol:
                    return p["quantity"]
            return 0

    def order_place(self, **kwargs):
        """
        Place an order
        """
        order_args = dict(product="MIS", validity="DAY", exchange=self.exchange)
        url = f"{self.base_url}/api/v1/orders"
        symbol = kwargs.pop("symbol")
        side = kwargs.pop("side")
        exchange = kwargs.get("exchange", self.exchange)
        token = self._get_instrument_token(exchange=exchange, symbol=symbol)
        kwargs["instrument_token"] = token
        kwargs["order_side"] = side
        kwargs["client_id"] = self.client_id
        kwargs["user_order_id"] = random.randint(0, 1e9)
        order_args.update({"exchange": exchange})
        order_args.update(kwargs)
        payload = order_args.copy()
        resp = requests.post(url, headers=self.headers, params=payload)
        return self._response(resp)

    def order_modify(self, **kwargs):
        """
        Place an order
        """
        url = f"{self.base_url}/api/v1/orders"
        symbol = kwargs.pop("symbol")
        exchange = kwargs.get("exchange", self.exchange)
        token = self._get_instrument_token(exchange=exchange, symbol=symbol)
        kwargs["instrument_token"] = token
        kwargs["client_id"] = self.client_id
        payload = kwargs.copy()
        resp = requests.put(url, headers=self.headers, params=payload)
        return self._response(resp)

    def order_cancel(self, oms_order_id):
        """
        Place an order
        """
        url = f"{self.base_url}/api/v1/orders/{oms_order_id}"
        payload = {"client_id": self.client_id}
        resp = requests.delete(url, headers=self.headers, params=payload)
        return self._response(resp)

    def place_bracket_order(self, **kwargs):
        """
        Place a bracket order
        """
        url = f"{self.base_url}/api/v1/orders/bracket"
        symbol = kwargs.pop("symbol")
        side = kwargs.pop("side")
        exchange = kwargs.get("exchange", self.exchange)
        token = self._get_instrument_token(exchange=self.exchange, symbol=symbol)
        kwargs["instrument_token"] = token
        kwargs["order_side"] = side
        kwargs["client_id"] = self.client_id
        kwargs["user_order_id"] = 1000
        payload = kwargs.copy()
        resp = requests.post(url, headers=self.headers, params=payload)
        return self._response(resp)

    def exit_bracket_order(self, **kwargs):
        """
        Exit at existing bracket order
        """
        url = f"{self.base_url}/api/v1/orders/bracket/"
        payload = kwargs.copy()
        resp = requests.delete(url, headers=self.headers, params=payload)
        return resp.json()

    def modify_all_by_symbol(self, symbol, **kwargs):
        """
        Modify all pending orders for the given symbol
        symbol
            symbol for which orders to be changed
        kwargs
            provide modifications in the form of arguments
        Note
        ----
        1) Not all order arguments are accepted and this could result
        in an error from broker
        2) oms_order_id is mandatory for modifying orders
        """
        orders = self.pending_orders()
        orders = self.filter(orders, symbol=symbol, **kwargs)
        responses = []
        if len(orders) == 0:
            # Return in case of no matching orders
            return responses
        for order in orders:
            order_id = order["oms_order_id"]
            symbol = order["symbol"]
            resp = self.order_modify(oms_order_id=order_id, symbol=symbol, **kwargs)
            responses.append(resp)
        return responses

    def modify_bracket_stop(self, symbol, stop, first=False, p=0, n=None):
        """
        Modify stop loss value for bracket order
        symbol
            symbol to modify
        stop
            stop loss price to modify - actual stop loss
        first
            whether to modify the first order or all orders
            By default, all orders are modified
            If first=True, only the first order is modified
        p
            percentage of total open quantity to modify stop price
        n
            number of orders to be closed
        Note
        ----
        1) This implementation is exclusive to this broker - master trust
        2) stop is the actual stop loss price
        3) stop, target is identified by status
        4) if both p and n, percentage takes precedence
        """
        orders = self.pending_orders()
        orders = self.filter(
            orders, symbol=symbol, product="BO", status="trigger pending"
        )
        responses = []
        url = f"{self.base_url}/api/v1/orders"
        if len(orders) == 0:
            # Return in case of no matching orders
            return responses
        total_quantity = sum([o.get("quantity", 0) for o in orders])
        threshold_to_exit = total_quantity
        p = min(p, 100)
        if p > 0:
            threshold_to_exit = int(total_quantity * p * 0.01)
        qty = 0
        if n is None:
            n = len(orders)
        if p > 0:
            for order in orders:
                q = order.get("quantity", 0)
                qty += q
                kwargs = {
                    "oms_order_id": order["oms_order_id"],
                    "trading_symbol": order["symbol"],
                    "order_type": order["order_type"],
                    "exchange": order["exchange"],
                    "quantity": order["quantity"],
                    "product": order["product"],
                    "validity": order["validity"],
                    "instrument_token": order["instrument_token"],
                    "trigger_price": stop,
                    "price": stop,
                    "client_id": self.client_id,
                }
                payload = kwargs.copy()
                resp = requests.put(url, headers=self.headers, params=payload)
                responses.append(self._response(resp))
                if qty > threshold_to_exit:
                    return responses
            return responses

        # This code is run only when ou need to modify by number of orders
        for i, order in enumerate(orders):
            if i >= n:
                # Since the number of orders to be squared off is met,
                # we exit the program
                return responses
            kwargs = {
                "oms_order_id": order["oms_order_id"],
                "trading_symbol": order["symbol"],
                "order_type": order["order_type"],
                "exchange": order["exchange"],
                "quantity": order["quantity"],
                "product": order["product"],
                "validity": order["validity"],
                "instrument_token": order["instrument_token"],
                "trigger_price": stop,
                "price": stop,
                "client_id": self.client_id,
            }
            payload = kwargs.copy()
            resp = requests.put(url, headers=self.headers, params=payload)
            responses.append(self._response(resp))
            if first:
                return responses
        return responses

    def modify_bracket_target(self, symbol, target, first=False, n=None, p=0):
        """
        Modify target value for bracket order
        symbol
            symbol to modify
        stop
            target price to modify - actual stop loss
        first
            If True, close only the first order
        n
            number of orders to close
        Note
        ----
        1) This implementation is exclusive to this broker - master trust
        2) target is the actual target price
        3) stop, target is identified by status
        first
            whether to modify the first order or all orders
            By default, all orders are modified
            If first=True, only the first order is modified
        """
        orders = self.pending_orders()
        orders = self.filter(orders, symbol=symbol, product="BO", status="open")
        responses = []
        url = f"{self.base_url}/api/v1/orders"
        if len(orders) == 0:
            # Return in case of no matching orders
            return responses
        total_quantity = sum([o.get("quantity", 0) for o in orders])
        threshold_to_exit = total_quantity
        p = min(p, 100)
        if p > 0:
            threshold_to_exit = int(total_quantity * p * 0.01)
        qty = 0
        if n is None:
            n = len(orders)

        if p > 0:
            for order in orders:
                q = order.get("quantity", 0)
                qty += q
                kwargs = {
                    "oms_order_id": order["oms_order_id"],
                    "trading_symbol": order["symbol"],
                    "order_type": order["order_type"],
                    "exchange": order["exchange"],
                    "quantity": order["quantity"],
                    "product": order["product"],
                    "validity": order["validity"],
                    "instrument_token": order["instrument_token"],
                    "price": target,
                    "client_id": self.client_id,
                }
                payload = kwargs.copy()
                resp = requests.put(url, headers=self.headers, params=payload)
                responses.append(self._response(resp))
                if qty > threshold_to_exit:
                    return responses
            return responses
        for i, order in enumerate(orders):
            if i >= n:
                # Since the number of orders to be squared off is met,
                # we exit the program
                return responses
            kwargs = {
                "oms_order_id": order["oms_order_id"],
                "trading_symbol": order["symbol"],
                "order_type": order["order_type"],
                "exchange": order["exchange"],
                "quantity": order["quantity"],
                "product": order["product"],
                "validity": order["validity"],
                "instrument_token": order["instrument_token"],
                "price": target,
                "client_id": self.client_id,
            }
            payload = kwargs.copy()
            resp = requests.put(url, headers=self.headers, params=payload)
            responses.append(self._response(resp))
            if first:
                return responses
        return responses

    def exit_bracket_by_symbol(self, symbol, first=False, p=0):
        """
        Exit bracket order by symbol
        symbol
            symbol to exit bracket order
        first
            whether to modify the first order or all orders
            By default, all orders are modified
            If first=True, only the first order is modified
        """
        orders = self.pending_orders()
        orders = self.filter(orders, symbol=symbol, product="BO", status="open")
        responses = []
        if len(orders) == 0:
            # Return in case of no matching orders
            return responses
        total_quantity = sum([o.get("quantity", 0) for o in orders])
        threshold_to_exit = total_quantity
        p = min(p, 100)
        if p > 0:
            threshold_to_exit = int(total_quantity * p * 0.01)
            print(f"Exit threshold = {total_quantity}, {p}, {threshold_to_exit}")
        qty = 0
        for order in orders:
            oms_order_id = order["oms_order_id"]
            q = order.get("quantity", 0)
            qty += q
            leg_order_indicator = order["leg_order_indicator"]
            kwargs = {
                "oms_order_id": oms_order_id,
                "leg_order_indicator": leg_order_indicator,
                "status": "open",
                "client_id": self.client_id,
            }
            if leg_order_indicator:
                response = self.exit_bracket_order(**kwargs)
            else:
                response = self.order_cancel(oms_order_id)
            responses.append(response)
            if qty > threshold_to_exit:
                return responses
            if first:
                return responses
        return responses

    def modify_all_orders_by_conditions(
        self, modifications: Dict = None, n: int = 0, **kwargs
    ) -> List:
        """
        Modify all orders by the given condition
        """
        responses = []
        url = f"{self.base_url}/api/v1/orders"
        if not (modifications):
            return responses
        orders = self.pending_orders()
        orders = self.filter(orders, **kwargs)
        if len(orders) == 0:
            return responses
        if n <= 0:
            n = len(orders)
        for i, order in enumerate(orders):
            if i >= n:
                # Since the number of orders to be squared off is met,
                # we exit the program
                return responses
            kwargs = {
                "oms_order_id": order["oms_order_id"],
                "instrument_token": order["instrument_token"],
                "exchange": order["exchange"],
                "product": order["product"],
                "validity": order["validity"],
                "order_type": order["order_type"],
                "quantity": order["quantity"],
                "client_id": self.client_id,
            }
            kwargs.update(modifications)
            payload = kwargs.copy()
            resp = requests.put(url, headers=self.headers, params=payload)
            responses.append(self._response(resp))
        return responses

    def cancel_all_orders_by_conditions(self, n: int = 0, **kwargs) -> List:
        """
        Modify all orders by the given condition
        """
        responses = []
        url = f"{self.base_url}/api/v1/orders"
        orders = self.pending_orders()
        orders = self.filter(orders, **kwargs)
        if len(orders) == 0:
            return responses
        if n <= 0:
            n = len(orders)
        for i, order in enumerate(orders):
            if i >= n:
                # Since the number of orders to be squared off is met,
                # we exit the program
                return responses
            oms_order_id = order["oms_order_id"]
            resp = self.order_cancel(oms_order_id)
            responses.append(resp)
        return responses
