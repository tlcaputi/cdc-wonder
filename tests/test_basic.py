"""Basic unit tests for cdc_wonder (no network required)."""

import pytest
import pandas as pd

from cdc_wonder import WonderQuery, load_opioid_deaths


class TestWonderQueryValidation:
    def test_unknown_dataset_raises(self):
        with pytest.raises(ValueError, match="Unknown dataset"):
            WonderQuery(dataset="fake", group_by=["state"])

    def test_empty_group_by_raises(self):
        with pytest.raises(ValueError, match="group_by must contain"):
            WonderQuery(dataset="mcd", group_by=[])

    def test_unknown_dimension_raises(self):
        with pytest.raises(ValueError, match="Unknown group_by dimension"):
            WonderQuery(dataset="mcd", group_by=["nonexistent"])

    def test_mutually_exclusive_ucd_raises(self):
        with pytest.raises(ValueError, match="Only one of"):
            WonderQuery(
                dataset="mcd",
                group_by=["state"],
                ucd_icd10=["C33"],
                ucd_drug_codes=["D1"],
            )

    def test_mutually_exclusive_mcd_raises(self):
        with pytest.raises(ValueError, match="Only one of"):
            WonderQuery(
                dataset="mcd",
                group_by=["state"],
                mcd_icd10=["T40.1"],
                mcd_drug_codes=["D1"],
            )

    def test_sex_normalisation(self):
        q = WonderQuery(dataset="mcd", group_by=["state"], sex=["female", "m"])
        assert q._demo_filters["sex"] == ["F", "M"]

    def test_age_alias(self):
        q = WonderQuery(dataset="mcd", group_by=["age", "state"])
        assert q._group_by == ["ten_year_age", "state"]

    def test_valid_construction(self):
        q = WonderQuery(
            dataset="mcd",
            group_by=["year", "state", "sex"],
            years=range(2015, 2021),
            mcd_icd10=["T40.1", "T40.2"],
        )
        assert q._group_by == ["year", "state", "sex"]
        assert q._demo_filters["years"] == ["2015", "2016", "2017", "2018", "2019", "2020"]
        assert q._mcd_icd10 == ["T40.1", "T40.2"]


class TestLoadOpioidDeaths:
    def test_returns_dataframe(self):
        df = load_opioid_deaths()
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0

    def test_expected_columns(self):
        df = load_opioid_deaths()
        for col in ["year", "state", "state_code", "sex", "deaths"]:
            assert col in df.columns, f"Missing column: {col}"

    def test_years_range(self):
        df = load_opioid_deaths()
        assert df["year"].min() >= 2000
        assert df["year"].max() <= 2025

    def test_sex_values(self):
        df = load_opioid_deaths()
        assert set(df["sex"].unique()) == {"Female", "Male"}
