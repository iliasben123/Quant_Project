"""Vérifie le mode validation du rapport sur des données synthétiques (sans lire les vraies données)."""

import numpy as np
import pandas as pd

from src.backtest import report
from src.data.loader import load_config


def fake_split(n_dev=300, n_val=100):
    index = pd.bdate_range("2010-01-01", periods=n_dev + n_val)
    tickers = [etf["ticker"] for etf in load_config()["universe"]]
    prices = np.linspace(100, 200, n_dev + n_val)
    full = {
        t: pd.DataFrame({"Open": prices, "High": prices, "Low": prices, "Close": prices, "Volume": 1000},
                        index=index)
        for t in tickers
    }
    return {
        "development": {t: df.iloc[:n_dev] for t, df in full.items()},
        "validation": {t: df.iloc[n_dev:] for t, df in full.items()},
    }


def test_validation_starts_on_first_validation_day_with_history(monkeypatch):
    splits = fake_split()
    monkeypatch.setattr(report, "load_split", lambda name, config: splits[name])

    _, runs = report.run_all(load_config(), "validation")
    first_val_day = next(iter(splits["validation"].values())).index[0]

    for result in runs.values():
        assert result.equity.index[0] == first_val_day
    strategy_run = next(iter(runs.values()))
    assert strategy_run.positions.iloc[0].sum() == strategy_run.positions.shape[1]


def test_development_starts_after_warmup(monkeypatch):
    splits = fake_split()
    monkeypatch.setattr(report, "load_split", lambda name, config: splits[name])

    strategy, runs = report.run_all(load_config(), "development")
    dev_index = next(iter(splits["development"].values())).index
    assert next(iter(runs.values())).equity.index[0] == dev_index[strategy.warmup + 1]
