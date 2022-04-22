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

@pytest.mark.parametrize("test_input, expected",
        [
            (('sbin', None), 'sbin'),
            (('irfc', 'eq'), 'irfc'),
            (('irfc', 'N1'), 'irfc-N1'),
            (('bhel', 'na'), 'bhel'),
            (('bhel', 'NAN'), 'bhel'),
            (('TCS', '-'), 'TCS'),
            (('TCS', pd.NA), 'TCS'),

            ]
        )
def test_get_name_for_cash_symbol(test_input, expected):
    assert get_name_for_cash_symbol(*test_input) == expected

@pytest.mark.parametrize("test_input, expected",
        [
            (('nifty', '2022-05-20'),'NIFTY20MAY22FUT'),
            (('nifty', pendulum.date(2021,7,13),'ce'),'NIFTY13JUL21FUT'),
            (('nifty', pendulum.date(2021,7,13),'ce',14500),'NIFTY13JUL2114500CALL'),
            (('nifty', pendulum.date(2021,7,13),'pe',14500),'NIFTY13JUL2114500PUT'),
            (('sbin', pendulum.date(2021,7,13),'xx',14500),'SBIN13JUL21FUT'),
            ]
        )
def test_get_name_for_fno_symbol(test_input, expected):
    assert get_name_for_fno_symbol(*test_input) == expected
