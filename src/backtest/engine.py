"""Moteur de backtest vectorisé, en données journalières.

Modèle :
- le capital est divisé en N poches égales (une par ETF), jamais rééquilibrées ;
- une poche est investie à 100 % dans son ETF quand la position vaut 1, en cash (0 %) sinon ;
- le signal du jour t (calculé à la clôture) est exécuté à l'ouverture du jour t+1 ;
- les rendements sont mesurés d'ouverture à ouverture ;
- chaque changement de position coûte `cost_per_order` de la valeur de la poche.

Comme le cash ne rapporte rien, le gain total du portefeuille est exactement
égal à la somme des gains des trades.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

TRADE_COLUMNS = [
    "ticker", "entry_date", "exit_date", "entry_price", "exit_price",
    "days", "return", "pnl", "is_open",
]


@dataclass
class BacktestResult:
    equity: pd.Series         # valeur du portefeuille à l'ouverture de chaque jour
    sleeves: pd.DataFrame     # valeur de chaque poche à l'ouverture de chaque jour
    positions: pd.DataFrame   # position détenue d'une ouverture à la suivante (0/1)
    trades: pd.DataFrame      # un aller-retour par ligne (colonnes TRADE_COLUMNS)
    initial_capital: float
    cost_per_order: float

    @property
    def returns(self) -> pd.Series:
        """Rendements du portefeuille d'une ouverture à la suivante."""
        return self.equity.pct_change().dropna()


def run_backtest(
    data: dict[str, pd.DataFrame],
    signals: pd.DataFrame,
    initial_capital: float = 100_000.0,
    cost_per_order: float = 0.0005,
    start: pd.Timestamp | str | None = None,
) -> BacktestResult:
    """Simule une stratégie à partir de ses signaux.

    `start` : premier jour où une position peut être prise (avant : ignoré, capital en cash).
    """
    opens = pd.DataFrame({ticker: df["Open"] for ticker, df in data.items()})
    if not signals.index.equals(opens.index) or list(signals.columns) != list(opens.columns):
        raise ValueError("Les signaux doivent avoir les mêmes dates et tickers que les données.")
    if not 0 <= cost_per_order < 1:
        raise ValueError(f"cost_per_order invalide : {cost_per_order}")
    if opens.isna().any().any():
        raise ValueError("Prix d'ouverture manquants : nettoyer les données d'abord.")

    positions = signals.shift(1).fillna(0)
    if start is not None:
        opens = opens.loc[start:]
        positions = positions.loc[start:]
    if len(opens) < 2:
        raise ValueError("Il faut au moins 2 jours de données pour un backtest.")

    asset_returns = (opens.shift(-1) / opens - 1).iloc[:-1]
    positions = positions.iloc[:-1]

    changes = positions.diff().abs()
    changes.iloc[0] = positions.iloc[0].abs()

    growth = (1 - changes * cost_per_order) * (1 + positions * asset_returns)
    capital_per_sleeve = initial_capital / opens.shape[1]

    after = growth.cumprod() * capital_per_sleeve
    after.index = opens.index[1:]
    first = pd.DataFrame(capital_per_sleeve, index=opens.index[:1], columns=opens.columns)
    sleeves = pd.concat([first, after])

    return BacktestResult(
        equity=sleeves.sum(axis=1),
        sleeves=sleeves,
        positions=positions.astype(int),
        trades=extract_trades(positions, opens, sleeves, cost_per_order),
        initial_capital=initial_capital,
        cost_per_order=cost_per_order,
    )


def extract_trades(
    positions: pd.DataFrame,
    opens: pd.DataFrame,
    sleeves: pd.DataFrame,
    cost_per_order: float,
) -> pd.DataFrame:
    """Découpe les positions en allers-retours.

    Un trade encore ouvert à la fin est valorisé au dernier prix d'ouverture, sans frais de sortie.
    """
    last_date = opens.index[-1]
    rows = []
    for ticker in positions.columns:
        pos = positions[ticker]
        prev = pos.shift(1, fill_value=0)
        entries = pos.index[(pos == 1) & (prev == 0)]
        exits = pos.index[(pos == 0) & (prev == 1)]

        for entry in entries:
            later = exits[exits > entry]
            is_open = len(later) == 0
            exit_date = last_date if is_open else later[0]

            entry_price = opens.at[entry, ticker]
            exit_price = opens.at[exit_date, ticker]
            exit_cost = 0.0 if is_open else cost_per_order
            net = (1 - cost_per_order) * (exit_price / entry_price) * (1 - exit_cost)

            rows.append({
                "ticker": ticker,
                "entry_date": entry,
                "exit_date": exit_date,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "days": opens.index.get_loc(exit_date) - opens.index.get_loc(entry),
                "return": net - 1,
                "pnl": sleeves.at[entry, ticker] * (net - 1),
                "is_open": is_open,
            })

    trades = pd.DataFrame(rows, columns=TRADE_COLUMNS)
    return trades.sort_values("entry_date", ignore_index=True)
