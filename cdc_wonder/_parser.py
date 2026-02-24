# Copyright (c) 2026 Theodore Caputi
# SPDX-License-Identifier: MIT

"""Parse CDC WONDER TSV export into a clean pandas DataFrame."""

from __future__ import annotations

import csv
import io
import re

import pandas as pd


def parse_tsv(tsv_path: str) -> pd.DataFrame:
    """Read a CDC WONDER TSV file and return a clean DataFrame.

    CDC WONDER TSV files have a data section followed by a 'Query Parameters'
    footer. This function extracts only the data rows and normalises column
    names and values.

    Parameters
    ----------
    tsv_path : str
        Path to the downloaded .tsv file.

    Returns
    -------
    pd.DataFrame
        Raw data with original CDC column names but cleaned values.
        'Suppressed' death counts become NA. 'Unreliable' rates become NA.
    """
    # Try to read with UTF-8, fall back to latin-1 if needed
    try:
        with open(tsv_path, encoding="utf-8-sig") as f:
            raw = f.read()
    except UnicodeDecodeError:
        # CDC WONDER sometimes includes special characters; fall back to latin-1
        with open(tsv_path, encoding="latin-1") as f:
            raw = f.read()
    lines = raw.splitlines()

    # --- find the data header line ----------------------------------------------
    data_start = None
    for i, line in enumerate(lines):
        if re.match(r'"?Notes"?\t|"?Year"?\t|"?State"?\t|"?Month"?\t', line):
            data_start = i
            break
    if data_start is None:
        raise ValueError(
            f"Could not find data header in TSV. First 5 lines:\n"
            + "\n".join(repr(l) for l in lines[:5])
        )

    # --- collect data lines (stop at footer separator) -------------------------
    data_lines: list[str] = []
    for line in lines[data_start:]:
        stripped = line.strip()
        if stripped.startswith("---") or stripped == "":
            break
        data_lines.append(line)

    # --- parse via csv.DictReader ----------------------------------------------
    reader = csv.DictReader(io.StringIO("\n".join(data_lines)), delimiter="\t")
    rows = []
    for row in reader:
        notes = str(row.get("Notes", "")).strip().strip('"')
        if notes in ("Total", "Grand Total"):
            continue
        rows.append(
            {k.strip().strip('"'): (v.strip().strip('"') if v else "")
             for k, v in row.items()}
        )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # --- normalise numeric columns --------------------------------------------
    for col in df.columns:
        col_lower = col.lower()
        if "deaths" in col_lower or "population" in col_lower:
            mask_suppress = df[col].isin(["Suppressed", "Missing", "Not Applicable"])
            df[col] = pd.to_numeric(df[col].where(~mask_suppress), errors="coerce").astype("Int64")
        elif "rate" in col_lower or "percent" in col_lower:
            mask_bad = df[col].isin(["Unreliable", "Suppressed", "Not Applicable", "Missing", ""])
            df[col] = pd.to_numeric(df[col].where(~mask_bad), errors="coerce")

    return df.reset_index(drop=True)
