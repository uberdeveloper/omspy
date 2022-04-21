from omspy.brokers.kotak import *
from unittest.mock import patch, call
import pytest
import pendulum

@pytest.fixture
def mock_kotak():
    broker = Kotak("token", "userid", "password",
            "consumer_key", "access_code")
    with patch('ks_api_client.ks_api.KSTradeApi') as mock:
        broker.ksapi = mock
        return broker

@pytest.mark.parametrize("segment,date,expected",
        [
            ('cash', pendulum.datetime(2022,5,12), "https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_Cash_12_05_2022.txt"),
            ('futures', pendulum.datetime(2022,5,12), "https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_Cash_12_05_2022.txt"),
            ('fno', pendulum.datetime(2018,7,18), "https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_FNO_18_07_2018.txt"),
            ])
def test_get_url(segment, date, expected):
    with pendulum.test(date):
        assert get_url(segment) == expected

def test_get_url_no_segment():
    with pendulum.test(pendulum.datetime(2022,3,31)):
        assert get_url() == "https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_Cash_31_03_2022.txt"
