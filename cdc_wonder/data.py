# Copyright (c) 2026 Theodore Caputi
# SPDX-License-Identifier: MIT

"""Bundled dataset loader — opioid deaths 2000-2023, no network needed."""

from __future__ import annotations

import importlib.resources

import pandas as pd


def load_opioid_deaths(drop_metadata: bool = True) -> pd.DataFrame:
    """Return opioid overdose deaths by state, sex, and year (2000–2023).

    This is a pre-downloaded snapshot and requires no network access.
    To refresh from CDC WONDER, run WonderQuery directly.

    Source
    ------
    CDC WONDER MCD (D77: 2000–2020) + MCD Expanded (D157: 2021–2023).
    UCD filter : drug overdose all intents (D1+D2+D3+D4).
    MCD filter : T40.0, T40.1, T40.2, T40.3, T40.4, T40.6 (opioids).

    Parameters
    ----------
    drop_metadata : bool, default True
        Drop rows that don't look like real state-year-sex observations
        (year is missing or non-numeric, state is empty). Defends against
        future re-exports that accidentally include CDC WONDER footer rows.

    Returns
    -------
    pd.DataFrame
        Columns: year, state, state_code, sex, deaths, population, crude_rate
    """
    pkg = importlib.resources.files("cdc_wonder") / "data" / "opioid_deaths_by_state_gender.csv"
    with importlib.resources.as_file(pkg) as path:
        raw = pd.read_csv(path, dtype=str)

    raw.columns = [c.strip() for c in raw.columns]

    df = pd.DataFrame()
    df["year"]       = pd.to_numeric(raw["Year Code"], errors="coerce").astype("Int64")
    df["state"]      = raw["State"].str.strip()
    df["state_code"] = raw["State Code"].str.strip().str.zfill(2)
    df["sex"]        = raw["Sex"].str.strip()

    deaths_raw = raw["Deaths"].str.strip()
    df["deaths"] = pd.to_numeric(
        deaths_raw.where(deaths_raw != "Suppressed"), errors="coerce"
    ).astype("Int64")

    pop_raw = raw["Population"].str.strip()
    df["population"] = pd.to_numeric(
        pop_raw.where(pop_raw != ""), errors="coerce"
    ).astype("Int64")

    rate_raw = raw["Crude Rate"].str.strip()
    df["crude_rate"] = pd.to_numeric(
        rate_raw.where(~rate_raw.isin(["Unreliable", "Suppressed", "Not Applicable", ""])),
        errors="coerce"
    )

    if drop_metadata:
        keep = df["year"].notna() & df["state"].fillna("").ne("")
        df = df.loc[keep]

    return df.reset_index(drop=True)
