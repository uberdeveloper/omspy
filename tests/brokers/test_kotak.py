from omspy.brokers.kotak import *
from unittest.mock import patch, call
import pytest
import pendulum
import json
import os


@pytest.fixture
def mock_order_response():
    return {
        "Success": {
            "NSE": {
                "message": "Your AMO has been Modified: 13220426019512",
                "orderId": 13220426019512,
                "price": 115,
                "quantity": 1,
                "tag": "string",
            }
        }
    }


@pytest.fixture
def mock_kotak():
    broker = Kotak(
        "token",
        "userid",
        "password",
        "consumer_key",
        "access_code",
        instrument_master={"a": 100, "b": 200, "NSE:SYM": 1000},
    )
    with patch("ks_api_client.ks_api.KSTradeApi") as mock_broker:
        broker.client = mock_broker
        return broker


@pytest.mark.parametrize(
    "segment,date,expected",
    [
        (
            "cash",
            pendulum.datetime(2022, 5, 12),
            "https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_Cash_12_05_2022.txt",
        ),
        (
            "futures",
            pendulum.datetime(2022, 5, 12),
            "https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_Cash_12_05_2022.txt",
        ),
        (
            "fno",
            pendulum.datetime(2018, 7, 18),
            "https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_FNO_18_07_2018.txt",
        ),
    ],
)
def test_get_url(segment, date, expected):
    with pendulum.test(date):
        assert get_url(segment) == expected


def test_get_url_no_segment():
    with pendulum.test(pendulum.datetime(2022, 3, 31)):
        assert (
            get_url()
            == "https://preferred.kotaksecurities.com/security/production/TradeApiInstruments_Cash_31_03_2022.txt"
        )


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (("sbin", None), "sbin"),
        (("irfc", "eq"), "irfc"),
        (("irfc", "N1"), "irfc-N1"),
        (("bhel", "na"), "bhel"),
        (("bhel", "NAN"), "bhel"),
        (("TCS", "-"), "TCS"),
        (("TCS", pd.NA), "TCS"),
    ],
)
def test_get_name_for_cash_symbol(test_input, expected):
    assert get_name_for_cash_symbol(*test_input) == expected


@pytest.mark.parametrize(
    "test_input, expected, expected_type",
    [(17500.0, 17500, int), (22.96, 22.96, float), (18.396, 18.4, float)],
)
def test_convert_strike(test_input, expected, expected_type):
    assert convert_strike(test_input) == expected
    assert type(convert_strike(test_input)) == expected_type


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (("nifty", "2022-05-20"), "NIFTY20MAY22FUT"),
        (("nifty", "2022-05-20", "-", "-"), "NIFTY20MAY22FUT"),
        (("nifty", pendulum.date(2021, 7, 13), "ce"), "NIFTY13JUL21FUT"),
        (("nifty", pendulum.date(2021, 7, 13), "ce", 14500), "NIFTY13JUL2114500CALL"),
        (("nifty", pendulum.date(2021, 7, 13), "pe", 14500), "NIFTY13JUL2114500PUT"),
        (("sbin", pendulum.date(2021, 7, 13), "xx", 14500), "SBIN13JUL21FUT"),
    ],
)
def test_get_name_for_fno_symbol(test_input, expected):
    assert get_name_for_fno_symbol(*test_input) == expected


def test_download_file():
    url = get_url()
    test_df = pd.read_csv("tests/data/kotak_cash.csv")
    with patch("pandas.read_csv") as get:
        get.return_value = test_df
        df = download_file(url)
        assert len(df) == 7314


@pytest.mark.skipif(os.environ.get("SLOW") == "slow", reason="slow test")
def test_add_name_cash():
    df = pd.read_csv("tests/data/kotak_cash.csv")
    df2 = pd.read_csv("tests/data/kotak_cash_named.csv")
    df = add_name(df)
    assert len(df.columns) == 16
    assert "inst_name" in df
    pd.testing.assert_frame_equal(df, df2)


@pytest.mark.skipif(os.environ.get("SLOW") == "slow", reason="slow test")
def test_add_name_fno():
    df = pd.read_csv("tests/data/kotak_fno.csv")
    df2 = pd.read_csv("tests/data/kotak_fno_named.csv")
    df = add_name(df, "fno")
    assert len(df.columns) == 16
    assert "inst_name" in df
    assert len(df) == len(df2)
    m1 = df.head(5)
    m2 = df2.head(5)
    pd.testing.assert_frame_equal(df, df2)


def test_add_name_random():
    df = pd.read_csv("tests/data/kotak_cash.csv")
    df2 = add_name(df, "fix")
    assert len(df.columns) == 15
    pd.testing.assert_frame_equal(df, df2)


@pytest.mark.skipif(os.environ.get("SLOW") == "slow", reason="slow test")
def test_create_instrument_master():
    df = pd.read_csv("tests/data/kotak_cash.csv")
    df2 = pd.read_csv("tests/data/kotak_fno.csv")
    with open("tests/data/kotak_master.json") as f:
        expected = json.load(f)
    with patch("pandas.read_csv") as get:
        get.side_effect = [df, df2]
        master = create_instrument_master()
        assert master == expected


def test_authenticate():
    broker = Kotak(
        "token",
        "userid",
        "password",
        "consumer_key",
        "access_code",
        instrument_master={"a": 100, "b": 200},
    )
    assert hasattr(broker, "client") is False
    with patch("ks_api_client.ks_api.KSTradeApi") as mock_broker:
        broker.authenticate()
        assert hasattr(broker, "client") is True
        mock_broker.assert_called_once()
        mock_broker.return_value.login.assert_called_once()
        mock_broker.return_value.session_2fa.assert_called_once()
        assert broker.master == {"a": 100, "b": 200}
        assert broker._rev_master == {100: "a", 200: "b"}


def test_get_instrument_token(mock_kotak):
    assert mock_kotak.get_instrument_token("a") == 100
    assert mock_kotak.get_instrument_token("aa") is None


def test_order_place(mock_kotak):
    broker = mock_kotak
    broker.order_place(symbol="SYM", quantity=10, side="buy", exchange="NSE")
    print(broker.client.place_order.call_args_list)
    broker.client.place_order.assert_called_once()
    # TODO: Check kwargs passed


def test_positions(mock_kotak):
    broker = mock_kotak
    broker.master = {"NSE:BHEL": 878, "NSE:NIFTY28APR2216400PUT": 71377}
    broker._rev_master = {v: k for k, v in broker.master.items()}
    with open("tests/data/kotak_positions.json") as f:
        expected = json.load(f)
        broker.client.positions.side_effect = [expected]
        positions = broker.positions
        broker.client.positions.assert_called_once()
        assert len(positions) == 2
        assert [x["symbol"] for x in positions] == [
            "NSE:BHEL",
            "NSE:NIFTY28APR2216400PUT",
        ]
        assert "quantity" in positions[0]
        assert "quantity" in positions[1]
        assert "netTrdQtyLot" not in positions[0]


def test_orders(mock_kotak):
    broker = mock_kotak
    broker.master = {"NSE:BHEL": 878, "NSE:NIFTY28APR2216400PUT": 71377}
    broker._rev_master = {v: k for k, v in broker.master.items()}
    with open("tests/data/kotak_orders.json") as f:
        expected = json.load(f)
        broker.client.order_report.side_effect = [expected]
        orders = broker.orders
        broker.client.order_report.assert_called_once()
        symbols = ["NSE:BHEL"] * 4 + ["NSE:NIFTY28APR2216400PUT"] * 2 + ["NSE:BHEL"]
        assert [x["symbol"] for x in orders] == symbols
        assert len(orders) == 7
        for column in [
            "side",
            "filled_quantity",
            "quantity",
            "exchange_timestamp",
            "order_id",
            "exchange_order_id",
        ]:
            assert column in orders[0]


def test_order_modify(mock_kotak):
    broker = mock_kotak
    broker.order_modify(order_id=123456, quantity=10, side="buy")
    broker.client.modify_order.assert_called_once()
    # TODO: Check kwargs passed


def test_order_cancel(mock_kotak):
    broker = mock_kotak
    broker.order_cancel(order_id=123456)
    broker.client.cancel_order.assert_called_once()
    # TODO: Check kwargs passed


def test_response(mock_kotak, mock_order_response):
    broker = mock_kotak
    expected = mock_order_response["Success"]
    assert mock_kotak._response(mock_order_response) == expected


def test_get_order_id(mock_kotak, mock_order_response):
    broker = mock_kotak
    assert broker._get_order_id(mock_order_response) == 13220426019512
    assert type(broker._get_order_id(mock_order_response)) == int
