from omspy.brokers.fyers import Fyers
from unittest.mock import patch
import pytest
import json

with open("tests/data/fyers.json") as f:
    mock_data = json.load(f)


@pytest.fixture
def mock_fyers():
    broker = Fyers("app_id", "secret", "user_id", "password", "pan")
    with patch("fyers_api.fyersModel.FyersModel") as mock:
        broker.fyers = mock
    return broker


def test_profile(mock_fyers):
    broker = mock_fyers
    broker.fyers.get_profile.return_value = mock_data.get("profile")
    profile = broker.profile
    broker.fyers.get_profile.assert_called_once()
    assert profile == mock_data.get("profile")


def test_funds(mock_fyers):
    broker = mock_fyers
    broker.fyers.funds.return_value = mock_data.get("funds")
    funds = broker.funds
    broker.fyers.funds.assert_called_once()
    assert funds == mock_data.get("funds")
