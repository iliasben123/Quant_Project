"""Analyse de sensibilité des paramètres, sur la période de développement uniquement.

But : vérifier que les paramètres retenus sont sur un plateau de résultats stables,
pas sur un pic isolé. Ce script ne sert PAS à choisir les meilleurs paramètres.
Protocole et critères : research/journal.md, section Phase 4.

Usage (depuis la racine du projet) :
    python -m src.backtest.sensitivity
"""

from __future__ import annotations

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.metrics import summarize
from src.data.loader import load_config
from src.data.splitter import load_split
from src.strategies.trend_following import MovingAverageCrossover

SHORT_WINDOWS = [20, 30, 40, 50, 60, 75, 100]
LONG_WINDOWS = [100, 150, 200, 250, 300]

MIN_SHARE_BEAT_BENCHMARK = 0.80
MIN_SHARE_DRAWDOWN_OK = 0.80
MAX_NEIGHBOR_SHARPE_GAP = 0.15


def run_grid(data: dict[str, pd.DataFrame], config: dict) -> tuple[pd.DataFrame, dict, pd.Timestamp]:
    """Backtest de chaque couple (courte, longue), tous à partir de la même date."""
    bt = config["backtest"]
    capital, cost = bt["initial_capital"], bt["cost_per_order"]
    ma_type = config["strategy"]["ma_type"]
    start = next(iter(data.values())).index[max(LONG_WINDOWS)]

    rows = []
    for long in LONG_WINDOWS:
        for short in SHORT_WINDOWS:
            if short >= long:
                continue
            strategy = MovingAverageCrossover(short, long, ma_type)
            s = summarize(run_backtest(data, strategy.generate_signals(data), capital, cost, start))
            rows.append({
                "short": short, "long": long, "sharpe": s["sharpe"], "cagr": s["cagr"],
                "max_drawdown": s["max_drawdown"], "n_trades": s["n_trades"],
            })

    tickers = list(data)
    index = next(iter(data.values())).index
    always_long = pd.DataFrame(1, index=index, columns=tickers)
    benchmark = summarize(run_backtest(data, always_long, capital, cost, start))
    return pd.DataFrame(rows), benchmark, start


def neighbors(grid: pd.DataFrame, short: int, long: int) -> pd.DataFrame:
    """Voisins directs dans la grille (une case autour), hors la case elle-même."""
    si, li = SHORT_WINDOWS.index(short), LONG_WINDOWS.index(long)
    near_short = SHORT_WINDOWS[max(si - 1, 0) : si + 2]
    near_long = LONG_WINDOWS[max(li - 1, 0) : li + 2]
    mask = grid["short"].isin(near_short) & grid["long"].isin(near_long)
    mask &= ~((grid["short"] == short) & (grid["long"] == long))
    return grid[mask]


def robustness_checks(
    grid: pd.DataFrame, benchmark_sharpe: float, max_dd_limit: float, short: int, long: int
) -> list[tuple[str, str, bool]]:
    """Applique les 4 critères du protocole. Renvoie (critère, valeur, réussi)."""
    share_beat = (grid["sharpe"] >= benchmark_sharpe).mean()
    share_dd = (-grid["max_drawdown"] <= max_dd_limit).mean()
    all_positive = bool((grid["cagr"] > 0).all())
    ref = grid[(grid["short"] == short) & (grid["long"] == long)]["sharpe"].iloc[0]
    gap = abs(neighbors(grid, short, long)["sharpe"].mean() - ref)

    return [
        (f"Variantes avec Sharpe >= B&H ({benchmark_sharpe:.2f})", f"{share_beat:.0%}",
         share_beat >= MIN_SHARE_BEAT_BENCHMARK),
        (f"Variantes avec max drawdown <= {max_dd_limit:.0%}", f"{share_dd:.0%}",
         share_dd >= MIN_SHARE_DRAWDOWN_OK),
        ("Toutes les variantes ont un CAGR positif", "oui" if all_positive else "non", all_positive),
        (f"Écart Sharpe voisins / {short}-{long}", f"{gap:.2f}", gap < MAX_NEIGHBOR_SHARPE_GAP),
    ]


def pivot(grid: pd.DataFrame, column: str, fmt) -> pd.DataFrame:
    table = grid.pivot(index="short", columns="long", values=column)
    return table.apply(lambda col: col.map(lambda x: "" if pd.isna(x) else fmt(x)))


def main() -> None:
    config = load_config()
    data = load_split("development", config)
    ref_short, ref_long = config["strategy"]["short_window"], config["strategy"]["long_window"]

    grid, benchmark, start = run_grid(data, config)
    end = next(iter(data.values())).index[-1]

    print(f"Sensibilité : {len(grid)} variantes SMA, développement du {start:%Y-%m-%d} au {end:%Y-%m-%d}")
    print(f"Référence   : {ref_short}/{ref_long}   |   B&H 10 ETF : Sharpe {benchmark['sharpe']:.2f}, "
          f"CAGR {benchmark['cagr']:+.2%}, max DD {benchmark['max_drawdown']:.1%}")
    print("Lignes = moyenne courte, colonnes = moyenne longue\n")

    for column, title, fmt in [
        ("sharpe", "Sharpe", lambda x: f"{x:.2f}"),
        ("cagr", "CAGR", lambda x: f"{x:+.1%}"),
        ("max_drawdown", "Max drawdown", lambda x: f"{x:.1%}"),
        ("n_trades", "Nombre de trades", lambda x: f"{x:.0f}"),
    ]:
        print(f"{title} :")
        print(pivot(grid, column, fmt).to_string())
        print()

    print("Critères de robustesse (protocole du journal) :")
    checks = robustness_checks(
        grid, benchmark["sharpe"], config["success_criteria"]["max_drawdown"], ref_short, ref_long
    )
    for label, value, ok in checks:
        print(f"  [{'OK ' if ok else 'NON'}] {label} : {value}")
    verdict = "ROBUSTE" if all(ok for _, _, ok in checks) else "NON ROBUSTE"
    print(f"\nVerdict pour {ref_short}/{ref_long} : {verdict}")


if __name__ == "__main__":
    main()
