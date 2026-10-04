"""Téléchargement des données OHLCV journalières et stockage brut en CSV.

Usage (depuis la racine du projet) :
    python -m src.data.loader
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import yaml
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config" / "config.yaml"

OHLCV_COLUMNS = ["Open", "High", "Low", "Close", "Volume"]


def load_config(path: Path = CONFIG_PATH) -> dict:
    """Charge le fichier de configuration YAML."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def download_ticker(
    ticker: str,
    start: str,
    end: str | None,
    interval: str = "1d",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """Télécharge les bougies OHLCV d'un ticker.

    `end` est inclus (yfinance l'exclut, d'où le +1 jour). `None` = jusqu'à aujourd'hui.
    Renvoie un DataFrame vide si aucune donnée n'est disponible.
    """
    yf_end = None
    if end is not None:
        yf_end = (date.fromisoformat(end) + timedelta(days=1)).isoformat()

    df = yf.download(
        ticker,
        start=start,
        end=yf_end,
        interval=interval,
        auto_adjust=auto_adjust,
        progress=False,
        multi_level_index=False,
    )
    if df.empty:
        return df

    df = df[OHLCV_COLUMNS]
    df.index.name = "Date"
    return df


def save_raw(df: pd.DataFrame, ticker: str, config: dict) -> Path:
    """Enregistre les données brutes d'un ticker en CSV et renvoie le chemin du fichier."""
    storage = config["storage"]
    raw_dir = PROJECT_ROOT / config["paths"]["raw"]
    raw_dir.mkdir(parents=True, exist_ok=True)

    path = raw_dir / storage["file_pattern"].format(ticker=ticker)
    df.to_csv(path, date_format=storage["date_format"])
    return path


def download_universe(config: dict) -> dict[str, pd.DataFrame]:
    """Télécharge et enregistre tous les ETF de l'univers. Renvoie les données téléchargées."""
    source = config["data_source"]
    dates = config["dates"]
    tickers = [etf["ticker"] for etf in config["universe"]]

    results: dict[str, pd.DataFrame] = {}
    failures: list[str] = []

    print(f"Téléchargement de {len(tickers)} ETF depuis {dates['download_start']}...\n")
    for ticker in tickers:
        try:
            df = download_ticker(
                ticker,
                start=dates["download_start"],
                end=dates["download_end"],
                interval=source["interval"],
                auto_adjust=source["auto_adjust"],
            )
        except Exception as exc:
            print(f"  {ticker:<5} ÉCHEC : {exc}")
            failures.append(ticker)
            continue

        if df.empty:
            print(f"  {ticker:<5} ÉCHEC : aucune donnée reçue")
            failures.append(ticker)
            continue

        path = save_raw(df, ticker, config)
        results[ticker] = df
        print(
            f"  {ticker:<5} {len(df):>5} lignes  "
            f"{df.index[0]:%Y-%m-%d} → {df.index[-1]:%Y-%m-%d}  "
            f"→ {path.relative_to(PROJECT_ROOT)}"
        )

    print(f"\nTerminé : {len(results)} réussis, {len(failures)} échecs.")
    if failures:
        print(f"Échecs : {', '.join(failures)}")
    return results


if __name__ == "__main__":
    download_universe(load_config())
