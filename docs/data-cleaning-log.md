# Data Cleaning Log — Barcelona EPW / TMYx Weather File

> This log is **dataset-specific**. It documents the transformations applied to the primary cleaned dataset for Session 3.
>
> The overall multi-source architecture is documented in `docs/pipeline-architecture-v1.md`.

---

## Dataset under cleaning

- **Dataset:** Barcelona EPW / TMYx Weather File
- **Raw path:** `data/raw/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw`
- **Clean output:** `data/processed/barcelona-epw-tmyx-clean.parquet`
- **Cleaning module:** `src/clean_data.py`
- **Cleaning notebook:** `notebooks/02-data-cleaning.ipynb`
- **Maintainer:** Passive Design Advisor team
- **Last updated:** 2026-05-18

---

## Pipeline summary

- **Raw rows:** 8,760 hourly EPW records
- **Cleaned rows:** 8,760 hourly records
- **Retention:** 100%
- **Columns added:** derived timestamp fields and passive-design indicators
- **Columns dropped:** unused EPW fields not required for the first-pass rule engine
- **Wall-clock time on standard laptop:** fill after running `python src/clean_data.py`

---

## The transforms — every one logged

### Transform 1: `load_epw`

- **What it changed:** Loaded the raw `.epw` file into a dataframe and metadata dictionary using `pvlib.iotools.read_epw()`.
- **Why this and not the alternative:** Manual EPW parsing by column position is risky. The data-quality audit found that naive column mapping can confuse radiation and illuminance fields. A validated EPW reader reduces that risk.
- **Downstream effect:** The rule engine can trust that dry-bulb temperature, humidity, wind, GHI, DNI, and DHI fields are correctly mapped.
- **Reversibility:** Yes — raw EPW file remains unchanged in `data/raw/`.
- **Assertion that proves it worked:** The raw file exists and returns an hourly dataframe; later invariants confirm 8,760 records.

### Transform 2: `standardise_epw_columns`

- **What it changed:** Renamed EPW reader fields into explicit project names such as `dry_bulb_temp_c`, `relative_humidity_pct`, `wind_speed_m_s`, and `global_horizontal_radiation_wh_m2`.
- **Why this and not the alternative:** Unit-explicit names reduce mistakes in later rules. Generic names such as `temp_air` or `ghi` are easy to misread in a multi-source pipeline.
- **Downstream effect:** Strategy rules and output cards can cite readable climate indicators.
- **Reversibility:** Yes — raw dataframe is copied before renaming.
- **Assertion that proves it worked:** `require_columns()` checks that required source fields exist before selection.

### Transform 3: `parse_and_normalise_time`

- **What it changed:** Converted the EPW datetime index into an explicit `timestamp` column and derived `month`, `day`, and `hour_of_day`.
- **Why this and not the alternative:** Keeping time fields explicit supports monthly/seasonal climate indicators and avoids hidden dependence on dataframe index state.
- **Downstream effect:** Enables cooling-season checks, summer filters, night-purge checks, and monthly reporting.
- **Reversibility:** Mostly yes — timestamp is derived from the EPW index and raw file remains preserved.
- **Assertion that proves it worked:** Timestamp parsing must produce zero nulls; final invariants require unique timestamps.

### Transform 4: `select_passive_design_fields`

- **What it changed:** Kept only EPW fields required by the current Passive Design Advisor: temperature, RH, wind, wind direction, and solar radiation variables.
- **Why this and not the alternative:** The project does not need every EPW field for the first-pass scorecard. Selecting a smaller schema makes the downstream contract easier to inspect.
- **Downstream effect:** The cleaned parquet becomes a clear climate-input contract for Phase 4–7 development.
- **Reversibility:** Yes — unused EPW fields are not destroyed because the raw EPW remains in `data/raw/`.
- **Assertion that proves it worked:** Final schema check confirms all required fields are present.

### Transform 5: `coerce_numeric_fields`

- **What it changed:** Coerced all selected climate variables to numeric values.
- **Why this and not the alternative:** String-typed climate values would silently break thresholds and comparisons.
- **Downstream effect:** Rule-engine checks such as `dry_bulb_temp_c >= 26` and `wind_speed_m_s >= 1.5` work deterministically.
- **Reversibility:** Yes — raw file remains unchanged.
- **Assertion that proves it worked:** The transform raises `ValueError` if numeric coercion introduces null values.

### Transform 6: `assert_climate_ranges`

- **What it changed:** Did not modify values; validated broad physical plausibility ranges.
- **Why this and not the alternative:** We do not clip or impute climate data unless there is a confirmed error. For this EPW file, validation is safer than altering the baseline.
- **Downstream effect:** Prevents physically impossible climate values from entering strategy scoring.
- **Reversibility:** Not applicable — validation only.
- **Assertion that proves it worked:** Temperature, RH, wind speed, wind direction, and radiation fields must fall within broad allowed ranges.

### Transform 7: `add_passive_design_features`

- **What it changed:** Added transparent first-pass indicators: `season`, `is_summer`, `cooling_season_flag`, `night_flag`, `solar_radiation_total_wh_m2`, `overheating_hour_proxy`, `night_cooling_potential_flag`, and `wind_available_flag`.
- **Why this and not the alternative:** These are simple, explainable rule-engine inputs. They are not a learned prediction and not a full comfort model.
- **Downstream effect:** Supports passive strategy checks for shading, ventilation, night purge, thermal mass, and cooling risk.
- **Reversibility:** Yes — derived columns are added; original selected climate fields remain.
- **Assertion that proves it worked:** Final invariants require boolean indicator columns to be boolean and final schema to be complete.

### Transform 8: `assert_clean_invariants`

- **What it changed:** Did not modify data; validated final output.
- **Why this and not the alternative:** The processed parquet is a contract artifact for downstream sessions. It must fail loudly if schema or row count changes.
- **Downstream effect:** Phase 4–7 work can depend on a stable cleaned climate table.
- **Reversibility:** Not applicable — validation only.
- **Assertion that proves it worked:** Exactly 8,760 rows, unique non-null timestamp, complete final schema, and broad climate plausibility checks.

---

## What we did NOT clean — and why

| Issue | Why we left it | What downstream needs to know |
|---|---|---|
| EPW represents Barcelona El Prat Airport, not central Barcelona street canyons | This is a dataset limitation, not a cleaning error | Use Open Data BCN thermal comfort zones and morphology modifiers to localise interpretation |
| TMY months come from different source years | This is normal for TMY construction | Do not use this file for continuous real-year sequence analysis across month boundaries |
| Urban heat island is not directly measured | EPW has no intra-city spatial variation | Output must show caveat: airport baseline may underrepresent dense urban overheating |
| Full energy simulation variables are not generated | Session 3 is data preparation, not simulation | The final tool is a scoping advisor, not an EnergyPlus replacement |

---

## Cumulative effect — raw vs cleaned

Of 8,760 raw hourly EPW records, 8,760 are retained. The cleaning preserves the full annual hourly climate baseline while reducing the dataset to the fields required by the Passive Design Advisor. It adds transparent rule-engine indicators for cooling season, summer, night hours, overheating proxy, wind availability, and night cooling potential. The cleaned dataset is suitable for first-pass passive strategy scoring and climate indicator generation. It is **not** suitable by itself for predicting indoor comfort, measuring central Barcelona microclimate, or replacing detailed building energy simulation.

---

## Sign-off

The pipeline runs from raw to clean reproducibly:

- [ ] `python src/clean_data.py` produces `data/processed/barcelona-epw-tmyx-clean.parquet`
- [ ] Re-running on the same input produces an identical parquet
- [ ] `01-data-profiling.ipynb` re-run on the cleaned data confirms anomalies are resolved or documented
- [ ] All assertions in `assert_clean_invariants` pass
- [x] This log has one entry per transform

**Cleaned by:** Passive Design Advisor team  
**Reviewed by another team:** [fill after peer review]  
**Reviewer notes:** [fill after peer review]
