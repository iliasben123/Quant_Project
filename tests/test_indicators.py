import numpy as np
import pandas as pd
import pytest

from src.features.indicators import ema, moving_average, sma


def make_series(values):
    return pd.Series(values, index=pd.bdate_range("2020-01-01", periods=len(values)), dtype=float)


def random_walk(n=500, seed=0):
    rng = np.random.default_rng(seed)
    return make_series(100 * np.exp(np.cumsum(rng.normal(0, 0.01, n))))


def test_sma_known_values():
    result = sma(make_series([1, 2, 3, 4, 5]), 3)
    assert result.isna().sum() == 2
    assert result.dropna().tolist() == [2.0, 3.0, 4.0]


def test_ema_constant_series_and_warmup():
    result = ema(make_series([7.0] * 30), 10)
    assert result.isna().sum() == 9
    assert np.allclose(result.dropna(), 7.0)


@pytest.mark.parametrize("kind", ["sma", "ema"])
def test_no_look_ahead(kind):
    prices = random_walk()
    cut = 300
    altered = prices.copy()
    altered.iloc[cut + 1 :] *= 3.0

    original = moving_average(prices, 50, kind)
    modified = moving_average(altered, 50, kind)
    pd.testing.assert_series_equal(original.iloc[: cut + 1], modified.iloc[: cut + 1])


@pytest.mark.parametrize("window", [0, -5, 2.5])
def test_invalid_window(window):
    with pytest.raises(ValueError):
        sma(make_series([1, 2, 3]), window)


def test_unknown_kind():
    with pytest.raises(ValueError):
        moving_average(make_series([1, 2, 3]), 2, "wma")
