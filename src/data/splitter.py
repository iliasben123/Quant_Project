"""Découpage chronologique des données nettoyées et verrouillage de la période de test.

Usage (depuis la racine du projet) :
    python -m src.data.splitter

Pour lire les données ailleurs dans le projet, utiliser `load_split()`.
"""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from src.data.cleaner import clean_universe
from src.data.loader import PROJECT_ROOT, load_config

SPLIT_NAMES = ["development", "validation", "test"]
LOCK_FILE = "LOCKED.txt"
LOCK_MESSAGE = (
    "PERIODE DE TEST VERROUILLEE\n"
    "Ces données ne doivent être ni ouvertes, ni tracées, ni analysées avant le test final.\n"
    "Voir GUIDE_PROJET_QUANT.md, sections 0.5 et 0.6.\n"
)


class TestDataLockedError(PermissionError):
    """Tentative de lecture de la période de test verrouillée."""


def check_split_dates(splits: dict) -> None:
    """Vérifie que les périodes sont dans l'ordre, sans chevauchement ni trou."""
    for prev, nxt in zip(SPLIT_NAMES, SPLIT_NAMES[1:]):
        prev_end = splits[prev]["end"]
        if prev_end is None:
            raise ValueError(f"La période '{prev}' doit avoir une date de fin.")
        expected = pd.Timestamp(prev_end) + timedelta(days=1)
        if pd.Timestamp(splits[nxt]["start"]) != expected:
            raise ValueError(
                f"'{nxt}' doit commencer le {expected:%Y-%m-%d}, "
                f"le lendemain de la fin de '{prev}' ({prev_end})."
            )


def split_dataframe(df: pd.DataFrame, splits: dict) -> dict[str, pd.DataFrame]:
    """Découpe un DataFrame en périodes (bornes incluses) et vérifie la couverture."""
    parts = {name: df.loc[splits[name]["start"] : splits[name]["end"]] for name in SPLIT_NAMES}

    n_assigned = sum(len(p) for p in parts.values())
    if n_assigned != len(df):
        raise ValueError(f"{len(df) - n_assigned} lignes hors des périodes définies.")
    for name, part in parts.items():
        if part.empty:
            raise ValueError(f"La période '{name}' ne contient aucune donnée.")
    return parts


def write_splits(parts_by_ticker: dict[str, dict[str, pd.DataFrame]], config: dict) -> None:
    """Enregistre chaque période dans son dossier, en remplaçant les anciens fichiers."""
    storage = config["storage"]
    for name in SPLIT_NAMES:
        out_dir = PROJECT_ROOT / config["paths"][name]
        out_dir.mkdir(parents=True, exist_ok=True)
        for old in out_dir.glob("*.csv"):
            old.unlink()
        for ticker, parts in parts_by_ticker.items():
            path = out_dir / storage["file_pattern"].format(ticker=ticker)
            parts[name].to_csv(path, date_format=storage["date_format"])

    if config["splits"]["test"].get("locked", True):
        lock_path = PROJECT_ROOT / config["paths"]["test"] / LOCK_FILE
        lock_path.write_text(LOCK_MESSAGE, encoding="utf-8")


def load_split(
    name: str,
    config: dict | None = None,
    tickers: list[str] | None = None,
    unlock_test: bool = False,
) -> dict[str, pd.DataFrame]:
    """Lit les données d'une période. La période 'test' exige `unlock_test=True`."""
    if name not in SPLIT_NAMES:
        raise ValueError(f"Période inconnue : '{name}'. Choix possibles : {SPLIT_NAMES}")
    config = config or load_config()
    if name == "test" and config["splits"]["test"].get("locked", True) and not unlock_test:
        raise TestDataLockedError(
            "La période de test est verrouillée. Elle ne s'ouvre qu'une seule fois, "
            "pour le test final (load_split('test', unlock_test=True))."
        )

    storage = config["storage"]
    tickers = tickers or [etf["ticker"] for etf in config["universe"]]
    folder = PROJECT_ROOT / config["paths"][name]
    data = {}
    for ticker in tickers:
        path = folder / storage["file_pattern"].format(ticker=ticker)
        if not path.exists():
            raise FileNotFoundError(f"{path} introuvable : lancer d'abord `python -m src.data.splitter`")
        data[ticker] = pd.read_csv(path, index_col=storage["date_column"], parse_dates=True)
    return data


def run(config: dict) -> None:
    """Pipeline complet : contrôle des dates, nettoyage, découpage, écriture."""
    check_split_dates(config["splits"])
    data = clean_universe(config)

    parts_by_ticker = {ticker: split_dataframe(df, config["splits"]) for ticker, df in data.items()}
    write_splits(parts_by_ticker, config)

    print("\nDécoupage :")
    sample = next(iter(parts_by_ticker.values()))
    total = sum(len(p) for p in sample.values())
    for name in SPLIT_NAMES:
        part = sample[name]
        folder = config["paths"][name]
        print(
            f"  {name:<12} {part.index[0]:%Y-%m-%d} → {part.index[-1]:%Y-%m-%d}  "
            f"{len(part):>5} jours ({len(part) / total:.0%})  → {folder} ({len(parts_by_ticker)} fichiers)"
        )
    print(f"\nPériode de test verrouillée : {config['paths']['test']}/{LOCK_FILE}")


if __name__ == "__main__":
    run(load_config())
