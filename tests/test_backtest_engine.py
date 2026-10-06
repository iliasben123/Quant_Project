"""Tests du moteur de backtest sur des données synthétiques au résultat connu."""

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import run_backtest
from src.strategies.trend_following import MovingAverageCrossover

CAPITAL = 100_000.0


def make_data(opens: dict[str, list[float]]) -> dict[str, pd.DataFrame]:
    n = len(next(iter(opens.values())))
    index = pd.bdate_range("2020-01-01", periods=n)
    return {
        t: pd.DataFrame({"Open": p, "High": p, "Low": p, "Close": p, "Volume": 1000}, index=index, dtype=float)
        for t, p in opens.items()
    }


def make_signals(data, values: dict[str, list[int]]) -> pd.DataFrame:
    index = next(iter(data.values())).index
    return pd.DataFrame(values, index=index)


def test_always_long_rising_prices():
    """+1 % par ouverture, signal toujours à 1 : position prise le 2e jour, 8 hausses de 1 %."""
    data = make_data({"A": [100 * 1.01**k for k in range(10)]})
    signals = make_signals(data, {"A": [1] * 10})
    cost = 0.001
    result = run_backtest(data, signals, CAPITAL, cost)
    assert result.equity.iloc[-1] == pytest.approx(CAPITAL * (1 - cost) * 1.01**8)
    assert result.equity.iloc[0] == CAPITAL


def test_always_cash_keeps_capital():
    data = make_data({"A": [100, 120, 80, 150, 90]})
    result = run_backtest(data, make_signals(data, {"A": [0] * 5}), CAPITAL, 0.001)
    assert (result.equity == CAPITAL).all()
    assert result.trades.empty


def test_round_trip_costs_on_flat_prices():
    """Prix constant : un aller-retour coûte exactement deux fois les frais."""
    data = make_data({"A": [100.0] * 6})
    cost = 0.002
    result = run_backtest(data, make_signals(data, {"A": [0, 1, 1, 0, 0, 0]}), CAPITAL, cost)
    assert result.equity.iloc[-1] == pytest.approx(CAPITAL * (1 - cost) ** 2)
    assert len(result.trades) == 1


def test_execution_timing_no_look_ahead():
    """Le prix saute de 100 à 150 entre l'ouverture du jour 2 et celle du jour 3.

    Signal au jour 2 (clôture) -> exécuté au jour 3 -> le saut est raté.
    Signal au jour 1 (clôture) -> exécuté au jour 2 -> le saut est capté.
    """
    data = make_data({"A": [100, 100, 100, 150, 150, 150]})
    late = run_backtest(data, make_signals(data, {"A": [0, 0, 1, 0, 0, 0]}), CAPITAL, 0.0)
    early = run_backtest(data, make_signals(data, {"A": [0, 1, 0, 0, 0, 0]}), CAPITAL, 0.0)
    assert late.equity.iloc[-1] == pytest.approx(CAPITAL)
    assert early.equity.iloc[-1] == pytest.approx(CAPITAL * 1.5)


def test_sleeves_are_independent():
    """Deux poches de 50 000 : A investie (+1 %/jour), B en cash."""
    data = make_data({"A": [100 * 1.01**k for k in range(6)], "B": [100, 50, 200, 10, 300, 100]})
    signals = make_signals(data, {"A": [1] * 6, "B": [0] * 6})
    result = run_backtest(data, signals, CAPITAL, 0.0)
    assert result.equity.iloc[-1] == pytest.approx(CAPITAL / 2 * 1.01**4 + CAPITAL / 2)


def test_trade_extraction():
    data = make_data({"A": [100, 100, 110, 121, 121, 100, 90, 99]})
    signals = make_signals(data, {"A": [1, 1, 0, 0, 0, 1, 1, 1]})
    cost = 0.001
    trades = run_backtest(data, signals, CAPITAL, cost).trades

    assert len(trades) == 2
    first, second = trades.iloc[0], trades.iloc[1]
    idx = data["A"].index

    assert first["entry_date"] == idx[1] and first["exit_date"] == idx[3]
    assert first["return"] == pytest.approx((1 - cost) ** 2 * 1.21 - 1)
    assert not first["is_open"]

    assert second["entry_date"] == idx[6] and second["exit_date"] == idx[7]
    assert second["return"] == pytest.approx((1 - cost) * 1.1 - 1)
    assert second["is_open"]


def test_trades_pnl_equals_total_profit():
    """Invariant : somme des gains des trades = gain total du portefeuille."""
    rng = np.random.default_rng(42)
    n = 800
    opens = {t: list(100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))) for t in ["A", "B", "C"]}
    data = make_data(opens)
    strategy = MovingAverageCrossover(10, 50)
    result = run_backtest(data, strategy.generate_signals(data), CAPITAL, 0.0005)

    assert len(result.trades) > 10
    assert result.trades["pnl"].sum() == pytest.approx(result.equity.iloc[-1] - CAPITAL)


def test_start_ignores_earlier_positions_and_charges_entry():
    """Avec `start`, le capital démarre en cash : une position déjà active est achetée (avec frais) au départ."""
    data = make_data({"A": [100.0] * 6})
    signals = make_signals(data, {"A": [1] * 6})
    cost = 0.001
    result = run_backtest(data, signals, CAPITAL, cost, start=data["A"].index[2])
    assert result.equity.index[0] == data["A"].index[2]
    assert result.equity.iloc[-1] == pytest.approx(CAPITAL * (1 - cost))
    assert result.trades.iloc[0]["entry_date"] == data["A"].index[2]


def test_mismatched_signals_raise():
    data = make_data({"A": [100.0] * 5})
    bad = pd.DataFrame({"B": [1] * 5}, index=data["A"].index)
    with pytest.raises(ValueError):
        run_backtest(data, bad)
