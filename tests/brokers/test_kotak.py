from omspy.brokers.kotak import Kotak
from unittest.mock import patch, call
import pytest

@pytest.fixture
def mock_kotak():
    broker = Kotak("token", "userid", "password",
            "consumer_key", "access_code")
    with patch('ks_api_client.ks_api.KSTradeApi') as mock:
        broker.ksapi = mock
        return broker

def test_basic(mock_kotak):
    pass
