import numpy as np
import pandas as pd
import pytest

from src.backtest.metrics import (
    cagr, max_drawdown, sharpe, sortino, trade_metrics, volatility, yearly_returns,
)


def series(values, start="2020-01-01"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_cagr_doubling_in_two_years():
    equity = pd.Series([100.0, 200.0], index=pd.to_datetime(["2020-01-01", "2021-12-31"]))
    years = (equity.index[1] - equity.index[0]).days / 365.25
    assert cagr(equity) == pytest.approx(2 ** (1 / years) - 1)


def test_max_drawdown_known_path():
    assert max_drawdown(series([100, 120, 90, 130, 65])) == pytest.approx(65 / 130 - 1)


def test_max_drawdown_rising_is_zero():
    assert max_drawdown(series([100, 101, 102, 103])) == 0


def test_sharpe_sortino_volatility_formulas():
    r = series([0.01, -0.005, 0.02, -0.01, 0.003, 0.0])
    arr = r.to_numpy()
    std = arr.std(ddof=1)
    downside = np.sqrt((np.minimum(arr, 0) ** 2).mean())
    assert volatility(r) == pytest.approx(std * np.sqrt(252))
    assert sharpe(r) == pytest.approx(arr.mean() / std * np.sqrt(252))
    assert sortino(r) == pytest.approx(arr.mean() / downside * np.sqrt(252))


def test_zero_volatility_gives_nan():
    r = series([0.0, 0.0, 0.0])
    assert np.isnan(sharpe(r))
    assert np.isnan(sortino(r))


def test_trade_metrics():
    trades = pd.DataFrame({
        "pnl": [100.0, -50.0, 300.0, -20.0, 10.0],
        "return": [0.10, -0.05, 0.30, -0.02, 0.01],
        "days": [10, 20, 30, 40, 50],
    })
    m = trade_metrics(trades)
    assert m["n_trades"] == 5
    assert m["win_rate"] == pytest.approx(3 / 5)
    assert m["profit_factor"] == pytest.approx(410 / 70)
    assert m["avg_win"] == pytest.approx((0.10 + 0.30 + 0.01) / 3)
    assert m["avg_loss"] == pytest.approx((-0.05 - 0.02) / 2)
    assert m["pnl_total"] == pytest.approx(340)
    assert m["pnl_without_top3"] == pytest.approx(340 - 410)


def test_yearly_returns():
    equity = pd.Series(
        [100.0, 110.0, 121.0, 108.9],
        index=pd.to_datetime(["2020-06-01", "2020-12-31", "2021-12-31", "2022-03-01"]),
    )
    result = yearly_returns(equity)
    assert list(result.index) == [2020, 2021, 2022]
    assert result.tolist() == pytest.approx([0.10, 0.10, -0.10])


def test_trade_metrics_empty():
    m = trade_metrics(pd.DataFrame(columns=["pnl", "return", "days"]))
    assert m["n_trades"] == 0
    assert np.isnan(m["win_rate"])
