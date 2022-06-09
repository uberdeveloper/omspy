from omspy.brokers.finvasia import *
import pytest
from unittest.mock import patch

@pytest.fixture
def broker():
    finvasia = Finvasia(
            'user_id', 'password', 'pin',
            'vendor_code', 'app_key', 'imei')
    with patch('omspy.brokers.api_helper.ShoonyaApiPy') as mock_broker:
        finvasia.finvasia = mock_broker
    return finvasia


def test_defaults(broker):
    assert broker._user_id == 'user_id'
    assert broker._password == 'password'
    assert broker._pin == 'pin'
    assert broker._vendor_code == 'vendor_code'
    assert broker._app_key == 'app_key'
    assert broker._imei == 'imei'
    assert hasattr(broker, 'finvasia')

def test_login(broker):
    broker.login()
    broker.finvasia.login.assert_called_once()
