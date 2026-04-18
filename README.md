# cdc-wonder

Programmatic Python interface to the [CDC WONDER](https://wonder.cdc.gov/) Multiple Cause of Death database. Uses Playwright browser automation to submit queries and return results as pandas DataFrames.

## Installation

Works on **macOS**, **Linux**, and **Windows**. Requires Python 3.9+.

```bash
pip install git+https://github.com/tlcaputi/cdc-wonder.git
playwright install chromium
```

### Updating to the latest version

This package is installed from GitHub, so `pip install --upgrade` alone won't pick up new commits. Use `--upgrade --force-reinstall` (or `--upgrade --no-deps` if you don't want to re-resolve dependencies):

```bash
pip install --upgrade --force-reinstall git+https://github.com/tlcaputi/cdc-wonder.git
```

To check which version you have installed:

```bash
python -c "import cdc_wonder, importlib.metadata as m; print(m.version('cdc-wonder'))"
```

### Linux system dependencies

If `playwright install` fails on Linux, you may need system dependencies:

```bash
playwright install --with-deps chromium
```

## Quick Start

```python
from cdc_wonder import WonderQuery

# Opioid overdose deaths by state, sex, and year (2015-2020)
df = WonderQuery(
    dataset="mcd",
    group_by=["year", "state", "sex"],
    years=range(2015, 2021),
    mcd_icd10=["T40.0", "T40.1", "T40.2", "T40.3", "T40.4"],
).run()

print(df.head())
```

## Bundled Data

A pre-downloaded opioid deaths dataset (by state, sex, year, 2000-2023) is included:

```python
from cdc_wonder import load_opioid_deaths
df = load_opioid_deaths()  # No network needed
```

## Datasets

| Dataset | ID | Years | Notes |
|---|---|---|---|
| `"mcd"` | D77 | 1999-2020 | Standard MCD |
| `"mcd_expanded"` | D157 | 2018-2023+ | Expanded race categories |

## Group-By Dimensions

Up to 5 dimensions per query:

- **Geographic:** `state`, `county`, `census_region`, `census_division`, `hhs_region`
- **Demographic:** `sex`, `race`, `hispanic`, `ten_year_age`, `five_year_age`, `single_year_age`
- **Time:** `year`, `month`, `weekday`
- **Cause:** `ucd_chapter`, `ucd_sub_chapter`, `ucd_code`, `ucd_113`, `mcd_chapter`, `mcd_sub_chapter`, `mcd_code`
- **Other:** `autopsy`, `place_of_death`, `urbanization_2013`

Aliases: `"age"` = `"ten_year_age"`, `"region"` = `"census_region"`

## Demographic Filters

| Parameter | Values | Example |
|---|---|---|
| `sex` | `"F"`, `"M"` (also accepts `"female"`, `"male"`) | `sex=["F"]` |
| `race` | `"2106-3"` (White), `"2054-5"` (Black), `"A-PI"` (Asian/PI) | `race=["2106-3"]` |
| `hispanic` | `"2135-2"` (Hispanic), `"2186-2"` (Not Hispanic) | `hispanic=["2135-2"]` |
| `ten_year_age` | `"25-34"`, `"45-54"`, `"65-74"`, etc. | `ten_year_age=["65-74"]` |
| `weekday` | `"1"` (Sun) through `"7"` (Sat) | `weekday=["2"]` |
| `autopsy` | `"Y"`, `"N"`, `"U"` | `autopsy=["Y"]` |
| `place_of_death` | `"1"` (Hospital), `"4"` (Home), `"5"` (Hospice) | `place_of_death=["1"]` |
| `states` | FIPS codes | `states=["06", "36", "48"]` |
| `census_region` | `"Northeast"`, `"Midwest"`, `"South"`, `"West"` | `census_region=["South"]` |

**Note on fine-grained age:** `five_year_age` and `single_year_age` filters require the same dimension in `group_by`:

```python
# Correct
df = WonderQuery(group_by=["five_year_age", "state"], five_year_age=["60-64", "65-69"]).run()

# Wrong - filter will be silently ignored
df = WonderQuery(group_by=["state"], five_year_age=["60-64"]).run()
```

## Cause-of-Death Filters

```python
# UCD ICD-10 codes (e.g., ischaemic heart disease I20-I25)
WonderQuery(group_by=["state"], ucd_icd10=["I20", "I21", "I22", "I23", "I24", "I25"])

# MCD ICD-10 codes (e.g., opioids)
WonderQuery(group_by=["state"], mcd_icd10=["T40.0", "T40.1", "T40.2"])

# UCD drug/alcohol classification
WonderQuery(group_by=["state"], ucd_drug_codes=["D1", "D2", "D3", "D4"])

# UCD ICD-10 113 cause list
WonderQuery(group_by=["state"], ucd_113_codes=["GR113-027"])

# UCD ICD-10 chapter
WonderQuery(group_by=["state"], ucd_icd_chapter=["C00-D48"])
```

Within each category (UCD, MCD), only one filter type can be active per query.

## Output

Returns a pandas DataFrame with:

- `Deaths` (Int64, NA for suppressed)
- `Population` (when available)
- `Crude Rate`, `Age-Adjusted Rate` (float64, NaN for unreliable/suppressed)
- Group-by columns (`State`, `Year`, `Sex`, etc.)

## Platform Support

Tested on macOS 15.5 (Apple Silicon) with Python 3.11. Should work on Linux
and Windows since all dependencies (pandas, Playwright) are cross-platform, but
these have not been tested.

| OS | Status |
|---|---|
| macOS (Apple Silicon) | Tested |
| macOS (Intel) | Untested, should work |
| Linux | Untested, should work |
| Windows 10/11 | Untested, should work |

## Requirements

- Python 3.9+
- pandas >= 1.3
- playwright >= 1.30

## Disclaimer

This package is not affiliated with, endorsed by, or maintained by the Centers
for Disease Control and Prevention (CDC). It automates interactions with the
publicly available [CDC WONDER](https://wonder.cdc.gov/) web interface. Users
are responsible for complying with CDC WONDER's
[terms of use](https://wonder.cdc.gov/mcd-icd10.html) and for verifying the
accuracy of any data retrieved.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. See the [LICENSE](LICENSE) file
for full terms.

## License

MIT License. Copyright (c) 2026 Theodore Caputi. See [LICENSE](LICENSE) for
details.
