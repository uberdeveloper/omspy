import os
from pathlib import Path, PurePath

from omspy.models import Candle, CandleStick, Timer
import pytest
import pendulum
from unittest.mock import patch
import pandas as pd

ROOT = PurePath(__file__).parent.parent / "tests" / "data"


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
    periods = pendulum.today(tz="local") - pendulum.datetime(2020, 1, 1, 0, tz="local")
    candles = []
    for p, prices in zip(periods, ohlc):
        candle = Candle(
            timestamp=p, open=prices[0], high=prices[1], low=prices[2], close=prices[3]
        )
        candles.append(candle)
    return candles


@pytest.fixture
def simple_candlestick():
    known = pendulum.datetime(2022, 1, 1, 0, 0)
    with pendulum.test(known):
        return CandleStick(symbol="NIFTY")


def test_candlestick_initial_settings(simple_candlestick):
    known = pendulum.datetime(2022, 1, 1)
    with pendulum.test(known):
        cdl = simple_candlestick
        assert cdl.symbol == "NIFTY"
        assert cdl.high == -1e100
        assert cdl.bar_high == -1e100
        assert cdl.low == 1e100
        assert cdl.bar_low == 1e100
        assert cdl.ltp == 0
        assert cdl.interval == 300
        assert cdl.timer.start_time == pendulum.today().add(hours=9, minutes=15)
        assert cdl.timer.end_time == pendulum.today().add(hours=15, minutes=30)
        assert cdl.next_interval == pendulum.today().add(hours=9, minutes=20)


def test_candlestick_add_candle(simple_candlestick):
    cdl = simple_candlestick
    cdl.symbol = "SBIN"
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


def test_candlestick_add_candle_extra_info(simple_candlestick):
    cdl = simple_candlestick
    cdl.symbol = "SBIN"
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


def test_candlestick_update_prices_initial_price(simple_candlestick):
    cdl = simple_candlestick
    cdl.ltp = 100
    cdl._update_prices()
    assert cdl.initial_price == 100

    cdl.ltp = 101
    cdl._update_prices()
    assert cdl.initial_price == 100
    assert cdl.high == 101


def test_candlestick_update_prices_candle(simple_candlestick):
    cdl = simple_candlestick
    for i in [100, 101, 102, 101, 103, 101, 99, 102]:
        # Manually changing properties
        cdl._last_ltp = cdl.ltp
        cdl.ltp = i
        cdl._update_prices()
    known = pendulum.datetime(2022, 1, 1, 9, 20, tz="local")
    with pendulum.test(known):
        ts = pendulum.now(tz="local")
        cdl.update_candle(timestamp=ts)
        candle = Candle(timestamp=ts, open=100, high=103, low=99, close=99)
        assert len(cdl.candles) == 1
        assert cdl.candles[0] == candle


def test_candlestick_bullish_bars(ohlc_data, simple_candlestick):
    cdl = simple_candlestick
    # TODO: Change this into a mock
    cdl.candles = ohlc_data
    assert cdl.bullish_bars == 4


def test_candlestick_bearish_bars(ohlc_data, simple_candlestick):
    cdl = simple_candlestick
    # TODO: Change this into a mock
    cdl.candles = ohlc_data
    assert cdl.bearish_bars == 2


@pytest.mark.parametrize(
    "interval,expected1,expected2",
    [
        (60, 374, pendulum.datetime(2022, 1, 1, 9, 16, tz="local")),
        (90, 249, pendulum.datetime(2022, 1, 1, 9, 16, 30, tz="local")),
        (300, 74, pendulum.datetime(2022, 1, 1, 9, 20, tz="local")),
    ],
)
def test_candlestick_periods(interval, expected1, expected2):
    known = pendulum.datetime(2022, 1, 1, tz="local")
    with pendulum.test(known.add(hours=9)):
        cdl = CandleStick(symbol="NIFTY", interval=interval)
        assert len(cdl.periods) == expected1
        assert cdl.next_interval == expected2


def test_candlestick_timezone():
    known = pendulum.datetime(2022, 1, 1, 0, 0)
    with pendulum.test(known):
        cdl = CandleStick(symbol="NIFTY", timezone="local")
        assert (
            cdl.timer.start_time.timezone_name == pendulum.now(tz="local").timezone_name
        )
        assert cdl.periods[0].timezone_name == pendulum.now(tz="local").timezone_name

    with pendulum.test(known):
        cdl = CandleStick(symbol="EURONEXT", timezone="Europe/Paris")
        assert cdl.timer.start_time.timezone_name == "Europe/Paris"
        assert cdl.periods[0].timezone_name == "Europe/Paris"


def test_candlestick_get_next_interval(simple_candlestick):
    cdl = simple_candlestick
    known = pendulum.datetime(2022, 1, 1, tz="local")
    with pendulum.test(known):
        assert cdl.next_interval == pendulum.datetime(2022, 1, 1, 9, 20, tz="local")
        assert len(cdl.periods) == 74
    with pendulum.test(known.add(hours=9, minutes=37)):
        assert cdl.get_next_interval() == pendulum.datetime(
            2022, 1, 1, 9, 40, tz="local"
        )
        assert len(cdl.periods) == 70
        assert cdl.periods[0] == pendulum.datetime(2022, 1, 1, 9, 45, tz="local")
    with pendulum.test(known.add(hours=15, minutes=21)):
        assert cdl.get_next_interval() == pendulum.datetime(
            2022, 1, 1, 15, 25, tz="local"
        )
        assert len(cdl.periods) == 1
        assert cdl.periods[0] == pendulum.datetime(2022, 1, 1, 15, 30, tz="local")
    with pendulum.test(known.add(hours=15, minutes=40)):
        assert cdl.get_next_interval() is None
        assert len(cdl.periods) == 0
        assert cdl.periods == []


def test_candlestick_update():
    # @@@ assumption [add test case]: this file location change breaks below paths
    known = pendulum.datetime(2022, 7, 1, 0, 0)
    with pendulum.test(known):
        cdl = CandleStick(symbol="NIFTY")
    df = pd.read_csv(ROOT / "nifty_ticks.csv", parse_dates=["timestamp"])
    for i, row in df.iterrows():
        ts = pendulum.instance(row["timestamp"], tz="local")
        ltp = row["last_price"]
        with pendulum.test(ts):
            cdl.update(ltp)
    candles = [
        Candle(
            timestamp=pendulum.datetime(2022, 7, 1, 9, 20, tz="local"),
            open=15695.7,
            high=15700.15,
            low=15651.35,
            close=15686.15,
        ),
        Candle(
            timestamp=pendulum.datetime(2022, 7, 1, 9, 25, tz="local"),
            open=15690.05,
            high=15715.80,
            low=15683.00,
            close=15712.5,
        ),
    ]
    assert cdl.candles == candles
    assert cdl.ltp == 15706.25
    assert cdl._last_ltp == 15703.25


def test_candlestick_update_interval():
    # @@@ assumption [add test case]: this file location change breaks below paths
    known = pendulum.datetime(2022, 7, 1, 0, 0, tz="local")
    df = pd.read_csv(ROOT / "nifty_ticks.csv", parse_dates=["timestamp"])
    # Only selecting the first 5 rows
    # TODO: To sync ticks with candles
    expected = pd.read_csv(
        ROOT / "nifty_candles_2min.csv", parse_dates=["timestamp"]
    ).iloc[:5]
    with pendulum.test(known):
        cdl = CandleStick(symbol="NIFTY", interval=120)
    candles = []
    for i, row in expected.iterrows():
        c = Candle(
            timestamp=pendulum.instance(row["timestamp"], tz="local"),
            open=row["open"],
            high=row["high"],
            low=row["low"],
            close=row["close"],
        )
        candles.append(c)
    for i, row in df.iterrows():
        ts = pendulum.instance(row["timestamp"], tz="local")
        ltp = row["last_price"]
        with pendulum.test(ts):
            cdl.update(ltp)
    print(len(cdl.candles))
    print(len(candles))
    assert cdl.candles == candles
    assert cdl.ltp == 15706.25
    assert cdl._last_ltp == 15703.25


def test_candlestick_last_bullish_bar_index(ohlc_data, simple_candlestick):
    cdl = simple_candlestick
    cdl.candles = ohlc_data
    assert cdl.last_bullish_bar_index == 6


def test_candlestick_last_bullish_bar_index_no_candle(ohlc_data, simple_candlestick):
    cdl = simple_candlestick
    assert cdl.last_bullish_bar_index == 0


def test_candlestick_last_bearish_bar_index(ohlc_data, simple_candlestick):
    cdl = simple_candlestick
    cdl.candles = ohlc_data
    assert cdl.last_bearish_bar_index == 5


def test_candlestick_last_bearish_bar_index_no_bar(ohlc_data, simple_candlestick):
    cdl = simple_candlestick
    cdl.candles = ohlc_data[:3]
    assert cdl.last_bearish_bar_index == 0


def test_candlestick_last_bullish_bar(ohlc_data, simple_candlestick):
    cdl = simple_candlestick
    cdl.candles = ohlc_data
    assert cdl.last_bullish_bar == Candle(
        timestamp=pendulum.datetime(2020, 1, 6, tz="local"),
        open=988,
        high=1031,
        low=970,
        close=1024,
    )


def test_candlestick_last_bearish_bar(ohlc_data, simple_candlestick):
    cdl = simple_candlestick
    cdl.candles = ohlc_data
    assert cdl.last_bearish_bar == Candle(
        timestamp=pendulum.datetime(2020, 1, 5, tz="local"),
        open=1038,
        high=1038,
        low=984,
        close=988,
    )


def test_candlestick_last_bars_no_bars(simple_candlestick):
    cdl = simple_candlestick
    assert cdl.last_bearish_bar is None
    assert cdl.last_bullish_bar is None
