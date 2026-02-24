# Copyright (c) 2026 Theodore Caputi
# SPDX-License-Identifier: MIT

"""
CDC WONDER dataset configurations.

Each dataset maps a friendly name to:
  url          - the form URL
  prefix       - the D* variable prefix (e.g. "D77")
  years        - list of available year strings
  group_by     - friendly name → B_* form value
  filters      - friendly name → select field name (V_* or F_* prefixed)
  ucd_drug_fld - form field for UCD drug/alcohol classification (O_ucd radio value)
  ucd_icd_fld  - form field name stem for UCD ICD-10 text search
  mcd_icd_fld  - form field name stem for MCD ICD-10 text search
  mcd_drug_fld - form field for MCD drug/alcohol classification (O_mcd radio value)
  ucd_chapter_fld - select field for UCD at ICD chapter level
"""

DATASETS = {
    "mcd": {
        "url": "https://wonder.cdc.gov/mcd-icd10.html",
        "prefix": "D77",
        "years": [str(y) for y in range(1999, 2021)],
        "group_by": {
            "census_region":  "D77.V10-level1",
            "census_division":"D77.V10-level2",
            "hhs_region":     "D77.V27-level1",
            "state":          "D77.V9-level1",
            "county":         "D77.V9-level2",
            "urbanization_2013": "D77.V19",
            "urbanization_2006": "D77.V11",
            "ten_year_age":   "D77.V5",
            "five_year_age":  "D77.V51",
            "single_year_age":"D77.V52",
            "infant_age":     "D77.V6",
            "sex":            "D77.V7",
            "hispanic":       "D77.V17",
            "race":           "D77.V8",
            "year":           "D77.V1-level1",
            "month":          "D77.V1-level2",
            "weekday":        "D77.V24",
            "autopsy":        "D77.V20",
            "place_of_death": "D77.V21",
            "ucd_chapter":    "D77.V2-level1",
            "ucd_sub_chapter":"D77.V2-level2",
            "ucd_code":       "D77.V2-level3",
            "ucd_113":        "D77.V4",
            "ucd_injury_intent": "D77.V22",
            "ucd_drug_level1":"D77.V25-level1",
            "ucd_drug_level2":"D77.V25-level2",
            "mcd_chapter":    "D77.V13-level1",
            "mcd_sub_chapter":"D77.V13-level2",
            "mcd_code":       "D77.V13-level3",
            "mcd_113":        "D77.V15",
            "mcd_drug_level1":"D77.V26-level1",
            "mcd_drug_level2":"D77.V26-level2",
        },
        # These use V_* or F_* select fields (not text-search mode)
        "filters": {
            "years":     "F_D77.V1",
            "states":    "F_D77.V9",
            "sex":       "V_D77.V7",
            "race":      "V_D77.V8",
            "hispanic":  "V_D77.V17",
            "ten_year_age":  "V_D77.V5",
            "five_year_age": "V_D77.V51",
            "single_year_age": "V_D77.V52",
            "autopsy":   "V_D77.V20",
            "place_of_death": "V_D77.V21",
            "weekday":   "V_D77.V24",
            "census_region": "F_D77.V10",
            "hhs_region": "F_D77.V27",
        },
        # UCD ICD-10 text-search (O_ucd=D77.V2; trigger finder-action-D77.V2-Search)
        "ucd_icd_fld":    "D77.V2",
        # UCD ICD chapter select (F_D77.V2, chapter-level ranges like C00-D48)
        "ucd_chapter_fld": "F_D77.V2",
        # UCD drug/alcohol classification (O_ucd=D77.V25; select F_D77.V25)
        "ucd_drug_fld":   "D77.V25",
        # UCD ICD-10 113 cause list (O_ucd=D77.V4; select V_D77.V4)
        "ucd_113_fld":    "D77.V4",
        # MCD ICD-10 text-search (O_mcd=D77.V13; trigger finder-action-D77.V13-Search)
        "mcd_icd_fld":    "D77.V13",
        # MCD drug/alcohol classification (O_mcd=D77.V26; select F_D77.V26)
        "mcd_drug_fld":   "D77.V26",
    },

    "mcd_expanded": {
        "url": "https://wonder.cdc.gov/mcd-icd10-expanded.html",
        "prefix": "D157",
        "years": [str(y) for y in range(2018, 2026)],
        "group_by": {
            "census_region":  "D157.V10-level1",
            "census_division":"D157.V10-level2",
            "hhs_region":     "D157.V27-level1",
            "state":          "D157.V9-level1",
            "county":         "D157.V9-level2",
            "urbanization_2013": "D157.V19",
            "urbanization_2006": "D157.V11",
            "ten_year_age":   "D157.V5",
            "five_year_age":  "D157.V51",
            "single_year_age":"D157.V52",
            "infant_age":     "D157.V6",
            "sex":            "D157.V7",
            "hispanic":       "D157.V17",
            "race":           "D157.V42",
            "year":           "D157.V1-level1",
            "month":          "D157.V1-level2",
            "weekday":        "D157.V24",
            "autopsy":        "D157.V20",
            "place_of_death": "D157.V21",
            "ucd_chapter":    "D157.V2-level1",
            "ucd_sub_chapter":"D157.V2-level2",
            "ucd_code":       "D157.V2-level3",
            "ucd_113":        "D157.V4",
            "ucd_injury_intent": "D157.V22",
            "ucd_drug_level1":"D157.V25-level1",
            "ucd_drug_level2":"D157.V25-level2",
            "mcd_chapter":    "D157.V13-level1",
            "mcd_sub_chapter":"D157.V13-level2",
            "mcd_code":       "D157.V13-level3",
            "mcd_113":        "D157.V15",
            "mcd_drug_level1":"D157.V26-level1",
            "mcd_drug_level2":"D157.V26-level2",
        },
        "filters": {
            "years":     "F_D157.V1",
            "states":    "F_D157.V9",
            "sex":       "V_D157.V7",
            "race":      "V_D157.V42",
            "hispanic":  "V_D157.V17",
            "ten_year_age":  "V_D157.V5",
            "five_year_age": "V_D157.V51",
            "single_year_age": "V_D157.V52",
            "autopsy":   "V_D157.V20",
            "place_of_death": "V_D157.V21",
            "weekday":   "V_D157.V24",
            "census_region": "F_D157.V10",
            "hhs_region": "F_D157.V27",
        },
        "ucd_icd_fld":    "D157.V2",
        "ucd_chapter_fld": "F_D157.V2",
        "ucd_drug_fld":   "D157.V25",
        "ucd_113_fld":    "D157.V4",
        "mcd_icd_fld":    "D157.V13",
        "mcd_drug_fld":   "D157.V26",
    },
}

# Friendly group-by aliases so users can type common shorthand
GROUP_BY_ALIASES = {
    "age":    "ten_year_age",
    "age10":  "ten_year_age",
    "age5":   "five_year_age",
    "age1":   "single_year_age",
    "region": "census_region",
}

# Human-readable sex values → form values
SEX_MAP = {"male": "M", "female": "F", "m": "M", "f": "F"}
