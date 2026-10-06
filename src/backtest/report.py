"""Rapport de backtest : stratégie comparée au buy & hold.

Usage (depuis la racine du projet) :
    python -m src.backtest.report                        # période de développement
    python -m src.backtest.report --period validation    # uniquement pour départager des variantes
"""

from __future__ import annotations

import argparse

import pandas as pd

from src.backtest.engine import BacktestResult, run_backtest
from src.backtest.metrics import summarize, yearly_returns
from src.data.loader import load_config
from src.data.splitter import load_split
from src.strategies.trend_following import MovingAverageCrossover

ROWS = [
    ("final_equity", "Capital final", lambda x: f"{x:,.0f} €".replace(",", " ")),
    ("total_return", "Rendement total", lambda x: f"{x:+.1%}"),
    ("cagr", "CAGR", lambda x: f"{x:+.2%}"),
    ("volatility", "Volatilité", lambda x: f"{x:.2%}"),
    ("sharpe", "Sharpe", lambda x: f"{x:.2f}"),
    ("sortino", "Sortino", lambda x: f"{x:.2f}"),
    ("max_drawdown", "Max drawdown", lambda x: f"{x:.1%}"),
    ("exposure", "Temps investi", lambda x: f"{x:.0%}"),
    ("n_trades", "Nombre de trades", lambda x: f"{x:d}"),
    ("win_rate", "Taux de réussite", lambda x: f"{x:.0%}"),
    ("avg_win", "Gain moyen / trade", lambda x: f"{x:+.1%}"),
    ("avg_loss", "Perte moyenne / trade", lambda x: f"{x:+.1%}"),
    ("profit_factor", "Profit factor", lambda x: f"{x:.2f}"),
    ("avg_days", "Durée moyenne (jours)", lambda x: f"{x:.0f}"),
    ("pnl_without_top3", "Gain sans les 3 meilleurs", lambda x: f"{x:,.0f} €".replace(",", " ")),
]


def load_with_history(period: str, config: dict) -> tuple[dict[str, pd.DataFrame], pd.Timestamp | None]:
    """Données de la période + historique antérieur pour le calcul des indicateurs.

    Les moyennes mobiles de la validation sont calculées avec la fin du développement
    (données passées, donc sans look-ahead). Le backtest commence au début de la période.
    """
    data = load_split(period, config)
    if period == "development":
        return data, None
    history = load_split("development", config)
    combined = {t: pd.concat([history[t], data[t]]) for t in data}
    first_day = next(iter(data.values())).index[0]
    return combined, first_day


def run_all(config: dict, period: str) -> tuple[MovingAverageCrossover, dict[str, BacktestResult]]:
    data, period_start = load_with_history(period, config)
    strategy = MovingAverageCrossover.from_config(config)
    signals = strategy.generate_signals(data)

    first_tradable = signals.index[strategy.warmup + 1]
    start = first_tradable if period_start is None else max(first_tradable, period_start)

    bt = config["backtest"]
    capital, cost, stress = bt["initial_capital"], bt["cost_per_order"], bt["stress_cost_per_order"]
    always_long = pd.DataFrame(1, index=signals.index, columns=signals.columns)

    runs = {
        f"Stratégie {cost:.2%}": run_backtest(data, signals, capital, cost, start),
        f"Stratégie {stress:.2%}": run_backtest(data, signals, capital, stress, start),
        "B&H 10 ETF": run_backtest(data, always_long, capital, cost, start),
        "B&H SPY": run_backtest({"SPY": data["SPY"]}, always_long[["SPY"]], capital, cost, start),
    }
    return strategy, runs


def format_table(summaries: dict[str, dict]) -> pd.DataFrame:
    table = {}
    for name, s in summaries.items():
        table[name] = [
            "-" if pd.isna(s[key]) else fmt(s[key]) for key, _, fmt in ROWS
        ]
    return pd.DataFrame(table, index=[label for _, label, _ in ROWS])


def per_ticker(result: BacktestResult) -> pd.DataFrame:
    trades = result.trades
    grouped = trades.groupby("ticker", sort=False)
    table = pd.DataFrame({
        "trades": grouped.size(),
        "réussite": grouped["pnl"].apply(lambda p: f"{(p > 0).mean():.0%}"),
        "gain total €": grouped["pnl"].sum().round(0).astype(int),
        "meilleur trade €": grouped["pnl"].max().round(0).astype(int),
        "pire trade €": grouped["pnl"].min().round(0).astype(int),
    })
    return table.reindex(result.positions.columns)


def yearly_table(runs: dict[str, BacktestResult], main_name: str) -> tuple[pd.DataFrame, pd.Series]:
    """Rendements par année de la stratégie et des B&H, et écart avec le B&H 10 ETF."""
    names = [main_name, "B&H 10 ETF", "B&H SPY"]
    yearly = pd.DataFrame({name: yearly_returns(runs[name].equity) for name in names})
    gap = yearly[main_name] - yearly["B&H 10 ETF"]
    table = yearly.map(lambda x: f"{x:+.1%}")
    table["Écart vs B&H 10 ETF"] = gap.map(lambda x: f"{x:+.1%}")
    return table, gap


def check_criteria(strat: dict, bench: dict, criteria: dict) -> list[tuple[str, bool]]:
    return [
        (f"Sharpe >= {criteria['min_sharpe']}", strat["sharpe"] >= criteria["min_sharpe"]),
        (f"Max drawdown <= {criteria['max_drawdown']:.0%}", -strat["max_drawdown"] <= criteria["max_drawdown"]),
        ("Sharpe supérieur au B&H 10 ETF", strat["sharpe"] > bench["sharpe"]),
        ("Rentable sans les 3 meilleurs trades", strat["pnl_without_top3"] > 0),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Rapport de backtest")
    parser.add_argument("--period", choices=["development", "validation"], default="development")
    args = parser.parse_args()

    config = load_config()
    strategy, runs = run_all(config, args.period)
    summaries = {name: summarize(r) for name, r in runs.items()}
    main_name = next(iter(runs))
    main_summary = summaries[main_name]

    print(f"Stratégie : {strategy.describe()}")
    print(f"Période   : {args.period}, du {main_summary['start']:%Y-%m-%d} au {main_summary['end']:%Y-%m-%d}")
    print(f"Capital   : {config['backtest']['initial_capital']:,} €, poches égales par ETF\n".replace(",", " "))
    print(format_table(summaries).to_string())

    print(f"\nDétail par ETF ({main_name}) :")
    print(per_ticker(runs[main_name]).to_string())

    table, gap = yearly_table(runs, main_name)
    first_year = table.index[0]
    print(f"\nRendement par année (l'année {first_year} est partielle) :")
    print(table.to_string())
    print(f"  Années où la stratégie bat le B&H 10 ETF : {(gap > 0).sum()} / {len(gap)}")

    criteria = config["success_criteria"]
    print(f"\nCritères de réussite (indicatif : la décision finale se prend sur le test) :")
    for label, ok in check_criteria(main_summary, summaries["B&H 10 ETF"], criteria):
        print(f"  [{'OK ' if ok else 'NON'}] {label}")
    print(
        f"  [ i ] {main_summary['n_trades']} trades sur cette période "
        f"(objectif : >= {criteria['min_trades_full_history']} sur l'historique complet)"
    )


if __name__ == "__main__":
    main()
