# Copyright (c) 2026 Theodore Caputi
# SPDX-License-Identifier: MIT

"""
cdc_wonder — Programmatic access to CDC WONDER Multiple Cause of Death data.

Quick start
-----------
>>> from cdc_wonder import WonderQuery

# Opioid deaths by state, sex, year (2000–2020)
>>> df = WonderQuery(
...     dataset="mcd",
...     group_by=["year", "state", "sex"],
...     years=range(2000, 2021),
...     ucd_drug_codes=["D1", "D2", "D3", "D4"],
...     mcd_icd10=["T40.0", "T40.1", "T40.2", "T40.3", "T40.4", "T40.6"],
... ).run()

# Primary lung cancer deaths by state, year (113 cause list code)
>>> df = WonderQuery(
...     dataset="mcd",
...     group_by=["year", "state"],
...     years=range(2000, 2021),
...     ucd_113_codes=["GR113-027"],   # trachea, bronchus & lung cancer
... ).run()

# Pre-downloaded opioid data (no network needed)
>>> from cdc_wonder import load_opioid_deaths
>>> df = load_opioid_deaths()
"""

from .query import WonderQuery
from .data import load_opioid_deaths

__all__ = ["WonderQuery", "load_opioid_deaths"]
__version__ = "0.1.0"
