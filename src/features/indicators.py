"""Indicateurs techniques.

Tous les indicateurs sont causaux : la valeur au jour t ne dépend que des
données jusqu'au jour t inclus. Pas de valeur partielle pendant la période de
chauffe : on renvoie NaN tant que la fenêtre n'est pas complète.
"""

from __future__ import annotations

import pandas as pd


def _check_window(window: int) -> None:
    if not isinstance(window, int) or window < 1:
        raise ValueError(f"La fenêtre doit être un entier >= 1 (reçu : {window!r}).")


def sma(series: pd.Series, window: int) -> pd.Series:
    """Moyenne mobile simple sur `window` jours."""
    _check_window(window)
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, span: int) -> pd.Series:
    """Moyenne mobile exponentielle (span = nombre de jours équivalent)."""
    _check_window(span)
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


MOVING_AVERAGES = {"sma": sma, "ema": ema}


def moving_average(series: pd.Series, window: int, kind: str = "sma") -> pd.Series:
    """Moyenne mobile du type demandé ("sma" ou "ema")."""
    if kind not in MOVING_AVERAGES:
        raise ValueError(f"Type de moyenne inconnu : {kind!r}. Choix : {list(MOVING_AVERAGES)}")
    return MOVING_AVERAGES[kind](series, window)
