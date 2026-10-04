import numpy as np
import pandas as pd
import pytest

from src.strategies.trend_following import MovingAverageCrossover


def make_ohlcv(close):
    close = pd.Series(close, index=pd.bdate_range("2020-01-01", periods=len(close)), dtype=float)
    return pd.DataFrame({"Open": close, "High": close, "Low": close, "Close": close, "Volume": 1000})


def random_walk(n=600, seed=1):
    rng = np.random.default_rng(seed)
    return 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))


def test_rising_prices_are_long_after_warmup():
    strat = MovingAverageCrossover(5, 20)
    signals = strat.generate_signals({"X": make_ohlcv(np.linspace(100, 200, 100))})["X"]
    assert (signals.iloc[: strat.warmup] == 0).all()
    assert (signals.iloc[strat.warmup :] == 1).all()


def test_falling_prices_are_cash():
    strat = MovingAverageCrossover(5, 20)
    signals = strat.generate_signals({"X": make_ohlcv(np.linspace(200, 100, 100))})["X"]
    assert (signals == 0).all()


@pytest.mark.parametrize("ma_type", ["sma", "ema"])
def test_no_look_ahead(ma_type):
    strat = MovingAverageCrossover(20, 100, ma_type)
    close = random_walk()
    cut = 400
    altered = close.copy()
    altered[cut + 1 :] = altered[cut + 1 :][::-1] * 0.5

    original = strat.generate_signals({"X": make_ohlcv(close)})["X"]
    modified = strat.generate_signals({"X": make_ohlcv(altered)})["X"]
    pd.testing.assert_series_equal(original.iloc[: cut + 1], modified.iloc[: cut + 1])


def test_output_shape_and_values():
    strat = MovingAverageCrossover(10, 50)
    data = {"A": make_ohlcv(random_walk(seed=2)), "B": make_ohlcv(random_walk(seed=3))}
    signals = strat.generate_signals(data)
    assert list(signals.columns) == ["A", "B"]
    assert signals.index.equals(data["A"].index)
    assert set(np.unique(signals.values)) <= {0, 1}
    assert signals.isna().sum().sum() == 0


def test_invalid_parameters():
    with pytest.raises(ValueError):
        MovingAverageCrossover(200, 50)
    with pytest.raises(ValueError):
        MovingAverageCrossover(50, 200, "wma")


def test_describe():
    assert MovingAverageCrossover(50, 200).describe() == "MovingAverageCrossover(short=50, long=200, ma=sma)"
