"""Métriques de performance d'un backtest.

Conventions : 252 jours de bourse par an, taux sans risque = 0 %
(cohérent avec le cash rémunéré à 0 % dans le moteur).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.engine import BacktestResult

TRADING_DAYS = 252


def cagr(equity: pd.Series) -> float:
    """Rendement annuel composé, sur la durée calendaire réelle."""
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return float("nan")
    return (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1


def volatility(returns: pd.Series) -> float:
    """Volatilité annualisée."""
    return returns.std() * np.sqrt(TRADING_DAYS)


def sharpe(returns: pd.Series) -> float:
    std = returns.std()
    return float("nan") if std == 0 else returns.mean() / std * np.sqrt(TRADING_DAYS)


def sortino(returns: pd.Series) -> float:
    """Comme le Sharpe, mais seule la volatilité à la baisse est pénalisée."""
    downside = np.sqrt((returns.clip(upper=0) ** 2).mean())
    return float("nan") if downside == 0 else returns.mean() / downside * np.sqrt(TRADING_DAYS)


def drawdown(equity: pd.Series) -> pd.Series:
    """Baisse depuis le plus haut précédent (0 = au sommet, -0.3 = 30 % sous le sommet)."""
    return equity / equity.cummax() - 1


def max_drawdown(equity: pd.Series) -> float:
    return drawdown(equity).min()


def yearly_returns(equity: pd.Series) -> pd.Series:
    """Rendement de chaque année civile (la première et la dernière peuvent être partielles)."""
    year_end = equity.groupby(equity.index.year).last()
    previous = year_end.shift(1)
    previous.iloc[0] = equity.iloc[0]
    return year_end / previous - 1


def trade_metrics(trades: pd.DataFrame) -> dict:
    """Statistiques sur les allers-retours."""
    n = len(trades)
    if n == 0:
        nan = float("nan")
        return {"n_trades": 0, "win_rate": nan, "avg_win": nan, "avg_loss": nan,
                "profit_factor": nan, "avg_days": nan, "pnl_total": 0.0, "pnl_without_top3": 0.0}

    wins = trades[trades["pnl"] > 0]
    losses = trades[trades["pnl"] <= 0]
    gross_loss = -losses["pnl"].sum()
    return {
        "n_trades": n,
        "win_rate": len(wins) / n,
        "avg_win": wins["return"].mean() if len(wins) else float("nan"),
        "avg_loss": losses["return"].mean() if len(losses) else float("nan"),
        "profit_factor": wins["pnl"].sum() / gross_loss if gross_loss > 0 else float("inf"),
        "avg_days": trades["days"].mean(),
        "pnl_total": trades["pnl"].sum(),
        "pnl_without_top3": trades["pnl"].sum() - trades["pnl"].nlargest(3).sum(),
    }


def summarize(result: BacktestResult) -> dict:
    """Toutes les métriques d'un backtest."""
    equity, returns = result.equity, result.returns
    return {
        "start": equity.index[0],
        "end": equity.index[-1],
        "final_equity": equity.iloc[-1],
        "total_return": equity.iloc[-1] / equity.iloc[0] - 1,
        "cagr": cagr(equity),
        "volatility": volatility(returns),
        "sharpe": sharpe(returns),
        "sortino": sortino(returns),
        "max_drawdown": max_drawdown(equity),
        "exposure": result.positions.mean(axis=1).mean(),
        **trade_metrics(result.trades),
    }
