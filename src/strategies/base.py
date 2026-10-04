"""Modèle commun à toutes les stratégies.

Convention anti look-ahead :
- le signal du jour t est calculé avec les données connues à la clôture du jour t ;
- il n'est PAS décalé ici : le backtester l'exécute à l'ouverture du jour t+1.

Valeurs du signal : 1 = long, 0 = cash.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd


class Strategy(ABC):
    """Une stratégie reçoit des données OHLCV et renvoie un signal par actif et par jour."""

    allowed_signals: frozenset[int] = frozenset({0, 1})

    @property
    def name(self) -> str:
        return type(self).__name__

    @property
    @abstractmethod
    def params(self) -> dict:
        """Paramètres de la stratégie (servent au journal de recherche)."""

    @property
    def warmup(self) -> int:
        """Nombre de jours initiaux sans signal valide (période de chauffe)."""
        return 0

    def describe(self) -> str:
        args = ", ".join(f"{k}={v}" for k, v in self.params.items())
        return f"{self.name}({args})"

    @abstractmethod
    def compute_signal(self, ohlcv: pd.DataFrame) -> pd.Series:
        """Signal d'un seul actif. NaN autorisé pendant la période de chauffe."""

    def generate_signals(self, data: dict[str, pd.DataFrame]) -> pd.DataFrame:
        """Signaux de tous les actifs : une colonne par ticker, une ligne par jour.

        Les NaN de la période de chauffe sont remplacés par 0 (cash).
        """
        signals = {
            ticker: self._validate(self.compute_signal(ohlcv), ohlcv.index, ticker)
            for ticker, ohlcv in data.items()
        }
        return pd.DataFrame(signals)

    def _validate(self, signal: pd.Series, index: pd.Index, ticker: str) -> pd.Series:
        if not signal.index.equals(index):
            raise ValueError(f"{self.name} / {ticker} : l'index du signal ne correspond pas aux données.")
        invalid = set(signal.dropna().unique()) - self.allowed_signals
        if invalid:
            raise ValueError(f"{self.name} / {ticker} : valeurs de signal interdites {sorted(invalid)}.")
        return signal.fillna(0).astype(int)
