from pathlib import PurePath
from omspy.brokers.noren import *
from omspy.order import Order
import pytest
import yaml
import json
from unittest.mock import patch
import pendulum

DATA_ROOT = PurePath(__file__).parent.parent.parent / "tests" / "data"
BROKERS_ROOT = PurePath(__file__).parent


def test_noren_base():
    base = BaseNoren(host="https://api.noren.com", websocket="wss://api.noren.com")
    assert base._NorenApi__service_config["host"] == "https://api.noren.com"
    assert base._NorenApi__service_config["websocket_endpoint"] == "wss://api.noren.com"


def test_noren_defaults():
    noren = Noren(
        user_id="user_id",
        password="password",
        totp="totp",
        vendor_code="vendor_code",
        app_key="app_key",
        imei="imei",
        host="https://api.noren.com",
        websocket="wss://api.noren.com",
    )
    assert noren._user_id == "user_id"
    assert noren._password == "password"
    assert noren._totp == "totp"
    assert noren._vendor_code == "vendor_code"
    assert noren._app_key == "app_key"
    assert noren._imei == "imei"
    assert noren._NorenApi__service_config["host"] == "https://api.noren.com"
    assert (
        noren._NorenApi__service_config["websocket_endpoint"] == "wss://api.noren.com"
    )
