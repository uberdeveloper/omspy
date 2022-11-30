from pathlib import PurePath
from omspy.brokers.kotak import *
from unittest.mock import patch, call
import pytest
import pendulum
import json
import os

# @@@ assumption [add test case]: this file location change breaks below paths
DATA_ROOT = PurePath(__file__).parent.parent.parent / "tests" / "data"


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
    [(17500.0, 17500, int), (22.96, 22.96, float), (18.3963, 18.396, float)],
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
    test_df = pd.read_csv(DATA_ROOT / "kotak_cash.csv")
    with patch("pandas.read_csv") as get:
        get.return_value = test_df
        df = download_file(url)
        assert len(df) == 7314


@pytest.mark.skipif(os.environ.get("SLOW") == "slow", reason="slow test")
def test_add_name_cash():
    df = pd.read_csv(DATA_ROOT / "kotak_cash.csv")
    df2 = pd.read_csv(DATA_ROOT / "kotak_cash_named.csv")
    df = add_name(df)
    assert len(df.columns) == 16
    assert "inst_name" in df
    pd.testing.assert_frame_equal(df, df2)


@pytest.mark.skipif(os.environ.get("SLOW") == "slow", reason="slow test")
def test_add_name_fno():
    df = pd.read_csv(DATA_ROOT / "kotak_fno.csv")
    df2 = pd.read_csv(DATA_ROOT / "kotak_fno_named.csv")
    df = add_name(df, "fno")
    assert len(df.columns) == 16
    assert "inst_name" in df
    assert len(df) == len(df2)
    m1 = df.head(5)
    m2 = df2.head(5)
    pd.testing.assert_frame_equal(df, df2)


def test_add_name_random():
    df = pd.read_csv(DATA_ROOT / "kotak_cash.csv")
    df2 = add_name(df, "fix")
    assert len(df.columns) == 15
    pd.testing.assert_frame_equal(df, df2)


@pytest.mark.skipif(os.environ.get("SLOW") == "slow", reason="slow test")
def test_create_instrument_master():
    df = pd.read_csv(DATA_ROOT / "kotak_cash.csv")
    df2 = pd.read_csv(DATA_ROOT / "kotak_fno.csv")
    with open(DATA_ROOT / "kotak_master.json") as f:
        expected = json.load(f)
    with patch("pandas.read_csv") as get:
        get.side_effect = [df, df2, df, df2]
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
    broker.client.place_order.assert_called_once()
    # TODO: Check kwargs passed


def test_positions(mock_kotak):
    broker = mock_kotak
    broker.master = {"NSE:BHEL": 878, "NSE:NIFTY28APR2216400PUT": 71377}
    broker._rev_master = {v: k for k, v in broker.master.items()}
    keys_not_available = ["netTrdQtyLot", "buyTradedVal", "sellTradedVal", "lastPrice"]
    keys_to_check = ["quantity", "buy_value", "sell_value", "last_price"]
    with open(DATA_ROOT / "kotak_positions.json") as f:
        expected = json.load(f)
        broker.client.positions.side_effect = [expected]
        positions = broker.positions
        broker.client.positions.assert_called_once()
        assert len(positions) == 2
        assert [x["symbol"] for x in positions] == [
            "NSE:BHEL",
            "NSE:NIFTY28APR2216400PUT",
        ]
        for pos in positions:
            for key in keys_not_available:
                assert key not in pos
            for key in keys_to_check:
                assert key in pos


def test_orders(mock_kotak):
    broker = mock_kotak
    broker.master = {"NSE:BHEL": 878, "NSE:NIFTY28APR2216400PUT": 71377}
    broker._rev_master = {v: k for k, v in broker.master.items()}
    with open(DATA_ROOT / "kotak_orders.json") as f:
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


def tests_orders_status(mock_kotak):
    broker = mock_kotak
    broker.master = {
        "NSE:NIFTY28APR2217400CALL": 71530,
        "NSE:ESCORTS": 1099,
        "NSE:MANAPPURAM": 6035,
    }
    broker._rev_master = {v: k for k, v in broker.master.items()}
    with open(DATA_ROOT / "kotak_orders2.json") as f:
        mock_data = json.load(f)
        broker.client.order_report.side_effect = [mock_data]
        orders = broker.orders
        broker.client.order_report.assert_called_once()
        assert [x["status"] for x in orders] == ["COMPLETE"] * 7 + ["CANCELED"] * 5 + [
            "COMPLETE"
        ] * 6


def test_order_modify(mock_kotak):
    broker = mock_kotak
    broker.order_modify(order_id=123456, quantity=10, price=120, order_type="LIMIT")
    broker.client.modify_order.assert_called_once()
    broker.client.modify_order.assert_called_with(
        order_id="123456", quantity=10, price=120
    )


def test_order_modify_market(mock_kotak):
    broker = mock_kotak
    broker.order_modify(order_id=123456, quantity=10, price=120, order_type="MARKET")
    broker.client.modify_order.assert_called_once()
    broker.client.modify_order.assert_called_with(
        order_id="123456", quantity=10, price=0
    )


def test_order_modify_market_sl(mock_kotak):
    broker = mock_kotak
    broker.order_modify(
        order_id=123456, quantity=10, price=120, order_type="SL", trigger_price=115
    )
    broker.client.modify_order.assert_called_once()
    broker.client.modify_order.assert_called_with(
        order_id="123456", quantity=10, price=120, trigger_price=115
    )


def test_order_modify_extra_attributes(mock_kotak):
    broker = mock_kotak
    broker.order_modify(
        order_id=123456, quantity=10, price=120, order_type="MARKET", validity="GFD"
    )
    broker.client.modify_order.assert_called_once()
    broker.client.modify_order.assert_called_with(
        order_id="123456", quantity=10, price=0, validity="GFD"
    )


def test_order_cancel(mock_kotak):
    broker = mock_kotak
    broker.order_cancel(order_id=123456)
    broker.client.cancel_order.assert_called_once()
    broker.client.cancel_order.assert_called_with(order_id="123456")


def test_response(mock_kotak, mock_order_response):
    broker = mock_kotak
    expected = mock_order_response["Success"]
    assert mock_kotak._response(mock_order_response) == expected


def test_get_order_id(mock_kotak, mock_order_response):
    broker = mock_kotak
    assert broker._get_order_id(mock_order_response) == 13220426019512
    assert type(broker._get_order_id(mock_order_response)) == int


def test_get_status(mock_kotak):
    broker = mock_kotak
    assert broker.get_status("TRAD") == "COMPLETE"
    assert broker.get_status("trad") == "COMPLETE"
    assert broker.get_status("OPN") == "PENDING"
    assert broker.get_status("CAN") == "CANCELED"
    assert broker.get_status("MRF") == "PENDING"


def test_create_instrument_master_default():
    df = pd.read_csv(DATA_ROOT / "kotak_cash.csv").iloc[:100]
    df2 = pd.read_csv(DATA_ROOT / "kotak_fno.csv").iloc[:100]
    with patch("pandas.read_csv") as get:
        get.side_effect = [df, df2, df, df2]
        master = create_instrument_master()
    cash = add_name(df)
    fno = add_name(df2, "fno")
    df3 = pd.concat([cash, fno])
    expected = {
        k: int(v) for k, v in zip(df3.inst_name.values, df3.instrumenttoken.values)
    }
    assert master == expected


def test_create_instrument_master_different_columns():
    df = pd.read_csv(DATA_ROOT / "kotak_cash.csv").iloc[:100]
    df2 = pd.read_csv(DATA_ROOT / "kotak_fno.csv").iloc[:100]
    with patch("pandas.read_csv") as get:
        get.side_effect = [df, df2, df, df2]
        master = create_instrument_master(token="exchangetoken")
    cash = add_name(df)
    fno = add_name(df2, "fno")
    df3 = pd.concat([cash, fno])
    expected = {
        k: int(v) for k, v in zip(df3.inst_name.values, df3.exchangetoken.values)
    }
    assert master == expected

    with patch("pandas.read_csv") as get:
        get.side_effect = [df, df2, df, df2]
        master = create_instrument_master(name="instrumenttoken", token="exchangetoken")
    expected = {
        k: int(v) for k, v in zip(df3.instrumenttoken.values, df3.exchangetoken.values)
    }
    assert master == expected


def test_orders_exchange_timestamp(mock_kotak):
    broker = mock_kotak
    broker.master = {"NSE:BHEL": 878, "NSE:NIFTY28APR2216400PUT": 71377}
    broker._rev_master = {v: k for k, v in broker.master.items()}
    with open(DATA_ROOT / "kotak_orders.json") as f:
        expected = json.load(f)
        broker.client.order_report.side_effect = [expected]
        orders = broker.orders
        broker.client.order_report.assert_called_once()
        ts_array = [
            (2022, 4, 25, 12, 43, 28),
            (2022, 4, 25, 12, 55, 54),
            (2022, 4, 25, 12, 56, 55),
            (2022, 4, 25, 13, 5, 54),
            (2022, 4, 25, 13, 53, 8),
            (2022, 4, 25, 13, 54, 30),
            (2022, 4, 25, 15, 20, 40),
        ]
        expected_timestamp = [
            pendulum.datetime(*ts, tz="Asia/Kolkata") for ts in ts_array
        ]
        for order, ts in zip(orders, expected_timestamp):
            assert order["exchange_timestamp"] == ts
