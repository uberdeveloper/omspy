from omspy.base import Broker, pre, post
from typing import Optional, List, Dict
from urllib.parse import urlparse, parse_qs
from fyers_api import fyersModel, accessToken


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


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
    def __init__(self, app_id, secret, user_id, password, pan):
        self._app_id = app_id
        self._secret = secret
        self._user_id = user_id
        self._password = password
        self._pan = pan
        self._store_access_token = True
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
                client_id=self._app_id, token=access_token
            )
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
        driver.close()
