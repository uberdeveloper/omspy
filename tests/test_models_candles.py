from omspy.models import Candle, CandleStick
import pytest
import pendulum


@pytest.fixture
def ohlc_data():
    ohlc = [
        [1000, 1025, 974, 1013],
        [1013, 1048, 1029, 1032],
        [1033, 1045, 1024, 1040],
        [1040, 1059, 1037, 1039],
        [1038, 1038, 984, 988],
        [988, 1031, 970, 1024],
    ]
    periods = pendulum.today() - pendulum.datetime(2020, 1, 1, 0, 0)
    candles = []
    for p, prices in zip(periods, ohlc):
        candle = Candle(
            timestamp=p, open=prices[0], high=prices[1], low=prices[2], close=prices[3]
        )
        candles.append(candle)
    return candles


def test_candlestick_initial_settings():
    cdl = CandleStick(symbol="NIFTY")
    assert cdl.symbol == "NIFTY"
    assert cdl.high == -1e100
    assert cdl.bar_high == -1e100
    assert cdl.low == 1e100
    assert cdl.bar_low == 1e100
    assert cdl.ltp == 0


def test_candlestick_update():
    cdl = CandleStick(symbol="NIFTY")
    cdl.update(100)
    assert cdl.high == cdl.low == 100
    assert cdl.bar_high == cdl.low == 100

    cdl.update(102)
    assert cdl.high == cdl.bar_high == 102

    cdl.update(99)
    assert cdl.low == cdl.bar_low == 99

    cdl.update(101)
    assert cdl.high == cdl.bar_high == 102
    assert cdl.low == cdl.bar_low == 99


def test_candlestick_add_candle():
    cdl = CandleStick(symbol="SBIN")
    candle = Candle(
        timestamp=pendulum.now(tz="local"),
        open=100,
        high=110,
        low=96,
        close=105,
        volume=1e4,
    )
    cdl.add_candle(candle)
    assert len(cdl.candles) == 1
    assert cdl.candles[0] == candle


def test_candlestick_add_candle_extra_info():
    cdl = CandleStick(symbol="SBIN")
    candle = Candle(
        timestamp=pendulum.now(tz="local"),
        open=100,
        high=110,
        low=96,
        close=105,
        volume=1e4,
    )
    cdl.add_candle(candle)
    candle.info = "some extra info"
    cdl.add_candle(candle)
    assert cdl.candles[0].info is None
    assert cdl.candles[1].info == "some extra info"


def test_candlestick_update_initial_price():
    cdl = CandleStick(symbol="NIFTY")
    cdl.update(100)
    assert cdl.initial_price == 100

    cdl.update(101)
    assert cdl.initial_price == 100
    assert cdl.high == 101


def test_candlestick_update_candle():
    cdl = CandleStick(symbol="AAPL")
    for i in [100, 101, 102, 101, 103, 101, 99, 102]:
        cdl.update(i)
    ts = pendulum.now(tz="Asia/Kolkata")
    cdl.update_candle(timestamp=ts)
    candle = Candle(timestamp=ts, open=100, high=103, low=99, close=102)
    assert len(cdl.candles) == 1
    assert cdl.candles[0] == candle
    assert cdl.bar_high == cdl.bar_low == cdl.ltp == 102


def test_candlestick_update_multiple_candles():
    cdl = CandleStick(symbol="AAPL")
    for i in [100, 101, 102, 101, 103, 101, 99, 102]:
        cdl.update(i)
    ts = pendulum.parse("2020-01-01T09:00:00")
    cdl.update_candle(timestamp=ts)
    for i in [102.5, 104, 103, 102, 103]:
        cdl.update(i)
    ts = pendulum.parse("2020-01-01T09:30:00")
    cdl.update_candle(timestamp=ts)
    c1, c2 = cdl.candles[0], cdl.candles[1]
    assert len(cdl.candles) == 2
    assert c1.close == c2.open
    assert c2.timestamp == ts
    assert c2.open == 102
    assert c2.high == 104
    assert c2.low == 102
    assert cdl.high == 104
    assert cdl.low == 99


def test_bullish_bars(ohlc_data):
    cdl = CandleStick(symbol="sample")
    # TODO: Change this into a mock
    cdl.candles = ohlc_data
    assert cdl.bullish_bars == 4


def test_bearish_bars(ohlc_data):
    cdl = CandleStick(symbol="sample")
    # TODO: Change this into a mock
    cdl.candles = ohlc_data
    assert cdl.bearish_bars == 2
