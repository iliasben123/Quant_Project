"""Suivi de tendance : croisement de moyennes mobiles.

Règle : moyenne courte > moyenne longue -> LONG (1), sinon -> CASH (0).

Usage (depuis la racine du projet) :
    python -m src.strategies.trend_following    # résumé des signaux sur la période de développement
"""

from __future__ import annotations

import pandas as pd

from src.features.indicators import MOVING_AVERAGES, moving_average
from src.strategies.base import Strategy


class MovingAverageCrossover(Strategy):
    def __init__(self, short_window: int = 50, long_window: int = 200, ma_type: str = "sma"):
        if short_window >= long_window:
            raise ValueError(f"short_window ({short_window}) doit être < long_window ({long_window}).")
        if ma_type not in MOVING_AVERAGES:
            raise ValueError(f"ma_type inconnu : {ma_type!r}. Choix : {list(MOVING_AVERAGES)}")
        self.short_window = short_window
        self.long_window = long_window
        self.ma_type = ma_type

    @classmethod
    def from_config(cls, config: dict) -> MovingAverageCrossover:
        s = config["strategy"]
        return cls(s["short_window"], s["long_window"], s["ma_type"])

    @property
    def params(self) -> dict:
        return {"short": self.short_window, "long": self.long_window, "ma": self.ma_type}

    @property
    def warmup(self) -> int:
        return self.long_window - 1

    def compute_signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        close = ohlcv["Close"]
        ma_short = moving_average(close, self.short_window, self.ma_type)
        ma_long = moving_average(close, self.long_window, self.ma_type)

        signal = (ma_short > ma_long).astype(float)
        signal[ma_long.isna()] = float("nan")
        return signal


def summarize_signals(signals: pd.DataFrame, warmup: int) -> pd.DataFrame:
    """Temps passé en position longue et nombre d'entrées, hors période de chauffe."""
    active = signals.iloc[warmup:]
    return pd.DataFrame({
        "jours": len(active),
        "% long": (active.mean() * 100).round(1),
        "entrées": (active.diff() == 1).sum() + (active.iloc[0] == 1).astype(int),
    })


if __name__ == "__main__":
    from src.data.loader import load_config
    from src.data.splitter import load_split

    config = load_config()
    data = load_split("development", config)
    strategy = MovingAverageCrossover.from_config(config)
    signals = strategy.generate_signals(data)

    first = signals.index[strategy.warmup]
    print(f"Stratégie : {strategy.describe()}")
    print(f"Période   : développement, signaux valides du {first:%Y-%m-%d} au {signals.index[-1]:%Y-%m-%d}\n")
    summary = summarize_signals(signals, strategy.warmup)
    print(summary.to_string())
    print(f"\nTotal des entrées en position : {int(summary['entrées'].sum())}")
