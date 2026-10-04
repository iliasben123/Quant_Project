"""Validation, nettoyage et alignement des données brutes.

Ce module n'écrit aucun fichier : il fournit des données propres et alignées
au splitter, qui se charge de les découper et de les enregistrer.

Usage (depuis la racine du projet) :
    python -m src.data.cleaner      # rapport de contrôle uniquement
"""

from __future__ import annotations

import pandas as pd

from src.data.loader import OHLCV_COLUMNS, PROJECT_ROOT, load_config

PRICE_COLUMNS = ["Open", "High", "Low", "Close"]


class DataValidationError(Exception):
    """Problème bloquant détecté dans les données."""


def load_raw(ticker: str, config: dict) -> pd.DataFrame:
    """Lit le CSV brut d'un ticker."""
    storage = config["storage"]
    path = PROJECT_ROOT / config["paths"]["raw"] / storage["file_pattern"].format(ticker=ticker)
    if not path.exists():
        raise FileNotFoundError(f"{path} introuvable : lancer d'abord `python -m src.data.loader`")
    return pd.read_csv(path, index_col=storage["date_column"], parse_dates=True)


def clean_ticker(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Applique les corrections sans risque et renvoie (données, corrections effectuées)."""
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise DataValidationError(f"colonnes manquantes : {missing}")

    notes = []
    if not df.index.is_monotonic_increasing:
        df = df.sort_index()
        notes.append("dates triées")

    n_dup = int(df.index.duplicated().sum())
    if n_dup:
        df = df[~df.index.duplicated(keep="first")]
        notes.append(f"{n_dup} dates en double supprimées")

    df = df[OHLCV_COLUMNS].astype({c: "float64" for c in PRICE_COLUMNS})
    return df, notes


def validate_ticker(df: pd.DataFrame, config: dict) -> tuple[list[str], list[str]]:
    """Contrôle un DataFrame nettoyé et renvoie (erreurs bloquantes, alertes)."""
    rules = config["cleaning"]
    test_start = pd.Timestamp(config["splits"]["test"]["start"])
    tol = rules["price_tolerance"]
    errors: list[str] = []
    warnings: list[str] = []

    n_nan = int(df.isna().sum().sum())
    if n_nan:
        errors.append(f"{n_nan} valeurs manquantes")

    n_nonpos = int((df[PRICE_COLUMNS] <= 0).sum().sum())
    if n_nonpos:
        errors.append(f"{n_nonpos} prix nuls ou négatifs")

    n_hl = int((df["High"] < df["Low"]).sum())
    if n_hl:
        errors.append(f"{n_hl} jours avec High < Low")

    oc_max = df[["Open", "Close"]].max(axis=1)
    oc_min = df[["Open", "Close"]].min(axis=1)
    n_out = int(((oc_max > df["High"] * (1 + tol)) | (oc_min < df["Low"] * (1 - tol))).sum())
    if n_out:
        errors.append(f"{n_out} jours avec Open/Close hors de [Low, High]")

    n_negvol = int((df["Volume"] < 0).sum())
    if n_negvol:
        errors.append(f"{n_negvol} volumes négatifs")

    n_zerovol = int((df["Volume"] == 0).sum())
    if n_zerovol:
        warnings.append(f"{n_zerovol} jours avec un volume nul")

    gaps = df.index.to_series().diff().dt.days
    big_gaps = gaps[gaps > rules["max_gap_days"]]
    for day, n_days in big_gaps.items():
        warnings.append(f"trou de {int(n_days)} jours avant le {day:%Y-%m-%d}")

    returns = df["Close"].pct_change()
    extremes = returns[returns.abs() > rules["extreme_return_warning"]]
    for day, ret in extremes[extremes.index < test_start].items():
        warnings.append(f"variation extrême {ret:+.1%} le {day:%Y-%m-%d}")
    n_hidden = int((extremes.index >= test_start).sum())
    if n_hidden:
        warnings.append(f"{n_hidden} variations extrêmes dans la période de test (détails masqués)")

    return errors, warnings


def align_universe(data: dict[str, pd.DataFrame], common_start: str) -> dict[str, pd.DataFrame]:
    """Restreint tous les tickers aux dates communes, à partir de `common_start`."""
    common = None
    for df in data.values():
        common = df.index if common is None else common.intersection(df.index)
    common = common[common >= pd.Timestamp(common_start)]

    aligned = {}
    for ticker, df in data.items():
        dropped = df.index.difference(common)
        inner = dropped[dropped >= common[0]]
        if len(inner):
            print(f"  {ticker:<5} ALERTE : {len(inner)} dates absentes chez d'autres ETF supprimées")
        aligned[ticker] = df.loc[common]
    return aligned


def clean_universe(config: dict) -> dict[str, pd.DataFrame]:
    """Charge, nettoie, contrôle et aligne tout l'univers.

    Lève DataValidationError si au moins un ticker présente une erreur bloquante.
    """
    tickers = [etf["ticker"] for etf in config["universe"]]
    cleaned: dict[str, pd.DataFrame] = {}
    blocking: dict[str, list[str]] = {}

    print(f"Contrôle de {len(tickers)} ETF...\n")
    for ticker in tickers:
        try:
            df, notes = clean_ticker(load_raw(ticker, config))
        except DataValidationError as exc:
            blocking[ticker] = [str(exc)]
            print(f"  {ticker:<5} ERREUR : {exc}")
            continue

        errors, warnings = validate_ticker(df, config)
        if errors:
            blocking[ticker] = errors
        status = "ERREUR" if errors else ("ALERTE" if warnings else "OK")
        print(f"  {ticker:<5} {status:<7} {len(df):>5} lignes")
        for msg in notes:
            print(f"        correction : {msg}")
        for msg in errors:
            print(f"        erreur     : {msg}")
        for msg in warnings:
            print(f"        alerte     : {msg}")
        cleaned[ticker] = df

    if blocking:
        raise DataValidationError(
            "Erreurs bloquantes pour : " + ", ".join(blocking) + ". Corriger avant de continuer."
        )

    print("\nAlignement sur les dates communes...")
    aligned = align_universe(cleaned, config["dates"]["common_start"])
    first = next(iter(aligned.values()))
    print(f"  {len(first)} dates communes, du {first.index[0]:%Y-%m-%d} au {first.index[-1]:%Y-%m-%d}")
    return aligned


if __name__ == "__main__":
    clean_universe(load_config())
    print("\nContrôle terminé. Aucun fichier écrit (le splitter s'en charge).")
