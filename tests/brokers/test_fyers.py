from omspy.brokers.fyers import Fyers
from unittest.mock import patch
import pytest


@pytest.fixture
def mock_fyers():
    broker = Fyers("app_id", "secret", "user_id", "password", "pan")
    with patch("fyers_api.fyersModel.FyersModel") as mock:
        broker.fyers = mock
    return broker


def test_profile(mock_fyers):
    broker = mock_fyers
    broker.profile
    broker.fyers.get_profile.assert_called_once()
