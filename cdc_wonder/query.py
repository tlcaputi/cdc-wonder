# Copyright (c) 2026 Theodore Caputi
# SPDX-License-Identifier: MIT

"""WonderQuery: parameterized CDC WONDER MCD query."""

from __future__ import annotations

import os
import tempfile
from typing import Iterable

import pandas as pd

from ._datasets import DATASETS, GROUP_BY_ALIASES, SEX_MAP
from ._browser import run_query
from ._parser import parse_tsv


class WonderQuery:
    """Query CDC WONDER Multiple Cause of Death data programmatically.

    Parameters
    ----------
    dataset : str
        ``"mcd"``          — D77,  years 1999–2020
        ``"mcd_expanded"`` — D157, years 2018–2023+ (expanded race categories)

    group_by : list[str]
        Dimensions to group by (up to 5). Available names:

        Geographic:   "state", "county", "census_region", "census_division",
                      "hhs_region"
        Demographic:  "sex", "race", "hispanic", "ten_year_age", "five_year_age",
                      "single_year_age"
        Time:         "year", "month", "weekday"
        Cause:        "ucd_chapter", "ucd_sub_chapter", "ucd_code", "ucd_113",
                      "mcd_chapter", "mcd_sub_chapter", "mcd_code"
        Other:        "autopsy", "place_of_death", "urbanization_2013"

        Aliases: ``"age"`` → ``"ten_year_age"``

    years : iterable of int, optional
        Calendar years to include. ``None`` = all available years.
        For ``"mcd"``: 1999–2020. For ``"mcd_expanded"``: 2018–2023+.

    states : list[str], optional
        State FIPS codes to include, e.g. ``["06", "36", "48"]``.
        ``None`` = all states.

    sex : list[str], optional
        ``["F"]``, ``["M"]``, ``["F", "M"]`` (= all), or ``None``.
        Also accepts ``"male"``/``"female"``/``"m"``/``"f"``.

    ten_year_age, five_year_age, single_year_age : list[str], optional
        Age group codes from CDC WONDER. ``None`` = all ages.
        Example ten-year codes: ``["35-44", "45-54", "55-64"]``.

        **Note on five_year_age and single_year_age**: CDC WONDER hides these filters
        and only allows one age granularity per query. To use five_year_age or
        single_year_age filters, you must also group by that same dimension:

        >>> # Correct: Will filter and group by five-year ages
        >>> df = WonderQuery(
        ...     group_by=["five_year_age", "state"],
        ...     five_year_age=["60-64", "65-69"],
        ... ).run()

        >>> # Incorrect: Filter will be silently ignored (returns all ages)
        >>> df = WonderQuery(
        ...     group_by=["state"],
        ...     five_year_age=["60-64"],  # Ignored!
        ... ).run()

    race : list[str], optional
        Race codes from CDC WONDER (e.g. ``["1002-5", "2054-5", "A-PI"]``).
        ``None`` = all races.

    hispanic : list[str], optional
        Hispanic origin codes (e.g. ``["2135-2", "2186-2"]``). ``None`` = all.

    weekday : list[str], optional
        Weekday codes. ``None`` = all weekdays.

    autopsy : list[str], optional
        Autopsy status codes. ``None`` = all autopsy values.

    place_of_death : list[str], optional
        Place of death codes. ``None`` = all places.

    census_region : list[str], optional
        Census region codes. ``None`` = all regions.

    hhs_region : list[str], optional
        HHS region codes. ``None`` = all regions.

    ucd_icd10 : list[str], optional
        Filter deaths by **Underlying Cause of Death** ICD-10 codes.
        Uses text-search mode — accepts specific codes, ranges, or prefixes.
        Example: ``["C33", "C34"]`` for lung cancer.
        Mutually exclusive with ``ucd_drug_codes`` and ``ucd_icd_chapter``.

    ucd_icd_chapter : list[str], optional
        Filter UCD by ICD chapter range codes (chapter-level select).
        Example: ``["C00-D48"]`` for all neoplasms.
        Mutually exclusive with ``ucd_icd10`` and ``ucd_drug_codes``.

    ucd_drug_codes : list[str], optional
        Filter UCD by CDC drug/alcohol classification codes.
        Values: ``"D"`` (all drug-induced), ``"D1"`` (unintentional overdose,
        X40–X44), ``"D2"`` (suicide, X60–X64), ``"D3"`` (homicide, X85),
        ``"D4"`` (undetermined, Y10–Y14).
        Example: ``["D1", "D2", "D3", "D4"]`` for all-intent drug overdose.
        Mutually exclusive with ``ucd_icd10`` and ``ucd_icd_chapter``.

    mcd_icd10 : list[str], optional
        Filter deaths by **Multiple Cause of Death** ICD-10 codes.
        Uses text-search mode. Mutually exclusive with ``mcd_drug_codes``.
        Example: ``["T40.0", "T40.1", "T40.2", "T40.3", "T40.4", "T40.6"]``
        for opioid-involved deaths.

    mcd_drug_codes : list[str], optional
        Filter MCD by drug/alcohol classification codes (same values as
        ``ucd_drug_codes``). Mutually exclusive with ``mcd_icd10``.

    show_zeros : bool, default True
        Include rows where Deaths = 0.

    show_suppressed : bool, default True
        Include rows where CDC suppressed the count (< 10 deaths).

    headless : bool, default True
        Run browser in headless mode. Set ``False`` to watch the automation.

    verbose : bool, default False
        Print progress messages.

    Examples
    --------
    Opioid overdose deaths by state, sex, year (2000–2020):

    >>> from cdc_wonder import WonderQuery
    >>> df = WonderQuery(
    ...     dataset="mcd",
    ...     group_by=["year", "state", "sex"],
    ...     years=range(2000, 2021),
    ...     ucd_drug_codes=["D1", "D2", "D3", "D4"],
    ...     mcd_icd10=["T40.0", "T40.1", "T40.2", "T40.3", "T40.4", "T40.6"],
    ... ).run()

    Lung cancer deaths by state, year:

    >>> df = WonderQuery(
    ...     dataset="mcd",
    ...     group_by=["year", "state"],
    ...     years=range(2000, 2021),
    ...     ucd_icd10=["C33", "C34"],
    ... ).run()

    All-cause mortality by state, sex, age (2019–2020):

    >>> df = WonderQuery(
    ...     dataset="mcd",
    ...     group_by=["year", "state", "sex", "ten_year_age"],
    ...     years=[2019, 2020],
    ... ).run()
    """

    def __init__(
        self,
        dataset: str = "mcd",
        group_by: list[str] | None = None,
        years: Iterable[int] | None = None,
        states: list[str] | None = None,
        sex: list[str] | None = None,
        ten_year_age: list[str] | None = None,
        five_year_age: list[str] | None = None,
        single_year_age: list[str] | None = None,
        race: list[str] | None = None,
        hispanic: list[str] | None = None,
        weekday: list[str] | None = None,
        autopsy: list[str] | None = None,
        place_of_death: list[str] | None = None,
        census_region: list[str] | None = None,
        hhs_region: list[str] | None = None,
        ucd_icd10: list[str] | None = None,
        ucd_icd_chapter: list[str] | None = None,
        ucd_drug_codes: list[str] | None = None,
        ucd_113_codes: list[str] | None = None,
        mcd_icd10: list[str] | None = None,
        mcd_drug_codes: list[str] | None = None,
        show_zeros: bool = True,
        show_suppressed: bool = True,
        headless: bool = True,
        verbose: bool = False,
    ):
        # ── validate dataset ──────────────────────────────────────────────────
        if dataset not in DATASETS:
            raise ValueError(
                f"Unknown dataset {dataset!r}. Choose from: {list(DATASETS)}"
            )
        self._ds = DATASETS[dataset]

        # ── validate and normalise group_by ───────────────────────────────────
        if not group_by:
            raise ValueError("group_by must contain at least one dimension.")
        resolved = []
        for dim in group_by:
            dim_lower = dim.lower()
            dim_lower = GROUP_BY_ALIASES.get(dim_lower, dim_lower)
            if dim_lower not in self._ds["group_by"]:
                raise ValueError(
                    f"Unknown group_by dimension {dim!r} for dataset {dataset!r}.\n"
                    f"Available: {list(self._ds['group_by'])}"
                )
            resolved.append(dim_lower)
        self._group_by = resolved

        # ── validate mutual exclusions ────────────────────────────────────────
        n_ucd = sum(bool(x) for x in [ucd_icd10, ucd_icd_chapter, ucd_drug_codes, ucd_113_codes])
        if n_ucd > 1:
            raise ValueError(
                "Only one of ucd_icd10, ucd_icd_chapter, ucd_drug_codes, ucd_113_codes may be set."
            )
        if mcd_icd10 and mcd_drug_codes:
            raise ValueError("Only one of mcd_icd10, mcd_drug_codes may be set.")

        # ── normalise sex ─────────────────────────────────────────────────────
        if sex is not None:
            sex = [SEX_MAP.get(s.lower(), s.upper()) for s in sex]

        # ── build demographic filter dict ─────────────────────────────────────
        self._demo_filters: dict[str, list[str]] = {}
        if years is not None:
            self._demo_filters["years"] = [str(int(y)) for y in years]
        if states is not None:
            self._demo_filters["states"] = list(states)
        if sex is not None:
            self._demo_filters["sex"] = sex
        if race is not None:
            self._demo_filters["race"] = list(race)
        if hispanic is not None:
            self._demo_filters["hispanic"] = list(hispanic)
        if ten_year_age is not None:
            self._demo_filters["ten_year_age"] = list(ten_year_age)
        if five_year_age is not None:
            self._demo_filters["five_year_age"] = list(five_year_age)
        if single_year_age is not None:
            self._demo_filters["single_year_age"] = list(single_year_age)
        if weekday is not None:
            self._demo_filters["weekday"] = list(weekday)
        if autopsy is not None:
            self._demo_filters["autopsy"] = list(autopsy)
        if place_of_death is not None:
            self._demo_filters["place_of_death"] = list(place_of_death)
        if census_region is not None:
            self._demo_filters["census_region"] = list(census_region)
        if hhs_region is not None:
            self._demo_filters["hhs_region"] = list(hhs_region)

        self._ucd_icd10 = list(ucd_icd10) if ucd_icd10 else None
        self._ucd_chapter = list(ucd_icd_chapter) if ucd_icd_chapter else None
        self._ucd_drug = list(ucd_drug_codes) if ucd_drug_codes else None
        self._ucd_113 = list(ucd_113_codes) if ucd_113_codes else None
        self._mcd_icd10 = list(mcd_icd10) if mcd_icd10 else None
        self._mcd_drug = list(mcd_drug_codes) if mcd_drug_codes else None

        self._show_zeros = show_zeros
        self._show_suppressed = show_suppressed
        self._headless = headless
        self._verbose = verbose

    def run(self, tmp_dir: str | None = None) -> pd.DataFrame:
        """Execute the query and return a DataFrame.

        Parameters
        ----------
        tmp_dir : str, optional
            Directory for the intermediate .tsv file. Defaults to the system
            temp directory.

        Returns
        -------
        pd.DataFrame
            Raw CDC WONDER output with all original columns.
            Death count columns are Int64 (NA = suppressed).
            Rate columns are float64 (NaN = unreliable/suppressed).

        Raises
        ------
        ValueError
            If the returned data appears to be all-cause mortality when a
            specific cause filter was requested (safety check).
        """
        tmp_dir = tmp_dir or tempfile.gettempdir()
        tmp_tsv = os.path.join(tmp_dir, "_cdc_wonder_query.tsv")

        run_query(
            ds=self._ds,
            group_by=self._group_by,
            demographic_filters=self._demo_filters,
            ucd_icd10=self._ucd_icd10,
            ucd_chapter=self._ucd_chapter,
            ucd_drug_codes=self._ucd_drug,
            ucd_113_codes=self._ucd_113,
            mcd_icd10=self._mcd_icd10,
            mcd_drug_codes=self._mcd_drug,
            show_zeros=self._show_zeros,
            show_suppressed=self._show_suppressed,
            headless=self._headless,
            tmp_tsv=tmp_tsv,
            verbose=self._verbose,
        )

        df = parse_tsv(tmp_tsv)

        # Safety validation: check if we got all-cause mortality when a filter was applied
        self._validate_not_all_cause(df)

        return df

    def _validate_not_all_cause(self, df: pd.DataFrame) -> None:
        """Validate that filtered query didn't return all-cause mortality.

        If a UCD or MCD filter was requested but the returned data looks like
        all-cause mortality, raise an error. This catches cases where the filter
        silently failed to apply.

        Parameters
        ----------
        df : pd.DataFrame
            The query result to validate.

        Raises
        ------
        ValueError
            If filtered data appears to be all-cause mortality.
        """
        # Only validate if a filter was applied
        has_ucd_filter = bool(self._ucd_icd10 or self._ucd_chapter or
                              self._ucd_drug or self._ucd_113)
        has_mcd_filter = bool(self._mcd_icd10 or self._mcd_drug)

        if not (has_ucd_filter or has_mcd_filter):
            return  # No filter applied, skip validation

        if df.empty:
            return  # No data returned, skip validation

        # Estimate national total deaths by aggregating across years/states
        if "Deaths" in df.columns:
            total_deaths = df["Deaths"].sum()

            # Normalize by number of years: all-cause <50 is ~150K/year nationally.
            # No single cancer cause exceeds ~200K/year nationally for any age group.
            # This threshold must be per-year to avoid false positives on multi-year
            # queries where legitimate cause-specific totals accumulate into millions.
            year_col = next((c for c in df.columns if c.lower() == "year"), None)
            n_years = df[year_col].nunique() if year_col else 1
            deaths_per_year = total_deaths / max(n_years, 1)

            # All-cause <50 per year is ~140-160K nationally.
            # Threshold: if >200K deaths/year with a cause filter it is suspicious.
            all_cause_per_year_threshold = 200_000

            if deaths_per_year >= all_cause_per_year_threshold:
                # Data looks suspiciously like all-cause mortality
                filters_applied = []
                if self._ucd_icd10:
                    filters_applied.append(f"UCD ICD-10: {self._ucd_icd10}")
                if self._ucd_chapter:
                    filters_applied.append(f"UCD chapter: {self._ucd_chapter}")
                if self._ucd_drug:
                    filters_applied.append(f"UCD drug codes: {self._ucd_drug}")
                if self._ucd_113:
                    filters_applied.append(f"UCD 113 cause: {self._ucd_113}")
                if self._mcd_icd10:
                    filters_applied.append(f"MCD ICD-10: {self._mcd_icd10}")
                if self._mcd_drug:
                    filters_applied.append(f"MCD drug codes: {self._mcd_drug}")

                raise ValueError(
                    f"Safety validation failed: Requested cause-specific filter(s) but "
                    f"received ~{deaths_per_year:,.0f} deaths/year ({total_deaths:,} total "
                    f"over {n_years} year(s)), which exceeds the per-year all-cause <50 "
                    f"threshold (~200K/yr). This usually means the filter failed to apply.\n\n"
                    f"Filters applied:\n"
                    f"  {chr(10).join('  ' + f for f in filters_applied)}\n\n"
                    f"Known issue: UCD ICD-10 text search may not be working properly. "
                    f"Try using:\n"
                    f"  - ucd_113_codes for common conditions (e.g., GR113-051 for MI)\n"
                    f"  - ucd_drug_codes for drug-related causes\n"
                    f"  - mcd_icd10 for multiple cause filters (works reliably)"
                )
