import pandas as pd

from src.backtest.sensitivity import LONG_WINDOWS, SHORT_WINDOWS, neighbors, robustness_checks


def make_grid(sharpe=0.6, cagr=0.05, max_dd=-0.15, overrides=None):
    rows = [
        {"short": s, "long": l, "sharpe": sharpe, "cagr": cagr, "max_drawdown": max_dd, "n_trades": 50}
        for l in LONG_WINDOWS for s in SHORT_WINDOWS if s < l
    ]
    grid = pd.DataFrame(rows)
    for (s, l), values in (overrides or {}).items():
        for col, v in values.items():
            grid.loc[(grid["short"] == s) & (grid["long"] == l), col] = v
    return grid


def test_grid_size():
    assert len(make_grid()) == 34


def test_neighbors_of_50_200():
    found = neighbors(make_grid(), 50, 200)
    pairs = set(zip(found["short"], found["long"]))
    assert pairs == {(s, l) for s in (40, 50, 60) for l in (150, 200, 250)} - {(50, 200)}


def test_flat_grid_is_robust():
    checks = robustness_checks(make_grid(), benchmark_sharpe=0.5, max_dd_limit=0.25, short=50, long=200)
    assert all(ok for _, _, ok in checks)


def test_isolated_peak_is_not_robust():
    grid = make_grid(overrides={(50, 200): {"sharpe": 1.2}})
    checks = robustness_checks(grid, benchmark_sharpe=0.5, max_dd_limit=0.25, short=50, long=200)
    assert [ok for _, _, ok in checks] == [True, True, True, False]


def test_negative_cagr_fails():
    grid = make_grid(overrides={(20, 100): {"cagr": -0.01}})
    checks = robustness_checks(grid, benchmark_sharpe=0.5, max_dd_limit=0.25, short=50, long=200)
    assert checks[2][2] is False
