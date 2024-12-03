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


@pytest.fixture
def broker():
    noren = Noren("user_id", "password", "totpcode", "vendor_code", "app_key", "imei")
    with patch("omspy.brokers.noren.NorenApi") as mock_broker:
        noren.noren = mock_broker
    return noren


@pytest.fixture
def mod():
    YAML_PATH = PurePath(__file__).parent.parent.parent / "omspy"
    with open(YAML_PATH / "brokers" / "finvasia.yaml") as f:
        return yaml.safe_load(f)


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


def test_login(broker):
    broker.login()
    broker.noren.login.assert_called_once()


def test_authenticate():
    # Patching with noren module
    with patch("omspy.brokers.noren.BaseNoren") as mock_broker:
        broker = Noren(
            "user_id", "password", "totpcode", "vendor_code", "app_key", "imei"
        )
        broker.authenticate()
        broker.noren.login.assert_called_once()
