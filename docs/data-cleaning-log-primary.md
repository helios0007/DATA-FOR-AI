# Data Cleaning Log — Barcelona EPW / TMYx Weather File

> Every transformation in the cleaning pipeline gets one row in this log.
> Save as `docs/data-cleaning-log.md`.

---

## Dataset under cleaning

- **Dataset:** Barcelona El Prat Airport — TMYx Typical Meteorological Year EPW
- **Primary project role:** primary baseline climate dataset for the Passive Design Advisor
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
- **Columns added:** 10 derived/project columns
- **Columns dropped:** unused auxiliary EPW fields not needed by the current rule engine
- **Wall-clock time on standard laptop:** fill after running `python src/clean_data.py`

---

## The transforms — every one logged

> **Transform 1:** `read_epw`
> - **What it changed:** Loaded the EPW file after skipping the 8-line metadata header and applied the official 35-column EPW schema.
> - **Why this and not the alternative:** Naive positional parsing can confuse radiation, illuminance, and extraterrestrial radiation fields. Explicit schema parsing reduces the risk of feeding the wrong solar variable into the rule engine.
> - **Downstream effect:** Solar and shading rules receive the correct irradiance fields.
> - **Reversibility:** Yes — the raw `.epw` file remains unchanged in `data/raw/`.
> - **Assertion that proves it worked:** `assert len(df_raw) == 8760`.

> **Transform 2:** `select_epw_fields`
> - **What it changed:** Kept only climate variables needed by the Passive Design Advisor: dry bulb temperature, dew point, RH, GHI, DNI, DHI, wind direction, wind speed, sky cover, and date fields.
> - **Why this and not the alternative:** The full EPW contains many fields that are irrelevant to current strategy checks. Keeping only needed fields reduces accidental misuse and makes the Phase 4 schema easier to defend.
> - **Downstream effect:** The cleaned parquet becomes a focused contract for passive strategy scoring.
> - **Reversibility:** Yes — dropped fields remain available in the raw EPW and can be re-added later.
> - **Assertion that proves it worked:** `assert set(SELECTED_COLUMNS).issubset(df.columns)`.

> **Transform 3:** `coerce_epw_numeric_fields`
> - **What it changed:** Converted selected EPW fields to numeric types and surfaced any parse failures as nulls.
> - **Why this and not the alternative:** Silent string values would break thresholds, aggregations, and plots. Numeric coercion makes invalid values measurable.
> - **Downstream effect:** All rule-engine thresholds operate on comparable numeric units.
> - **Reversibility:** Yes — raw file remains unchanged.
> - **Assertion that proves it worked:** `assert df[NUMERIC_COLUMNS].notna().all().all()` for required fields.

> **Transform 4:** `construct_epw_timestamp`
> - **What it changed:** Converted EPW hour format `1–24` into `0–23` and constructed a synthetic non-leap-year timestamp for ordering and grouping.
> - **Why this and not the alternative:** EPW TMY files are not real chronological years; therefore, the timestamp is only a deterministic index, not a historical date. This keeps analysis reproducible without pretending the TMY is a real year.
> - **Downstream effect:** Monthly summaries, plots, and grouping operations become stable and reproducible.
> - **Reversibility:** Yes — `source_year`, `month`, `day`, and `hour_raw_epw` are preserved.
> - **Assertion that proves it worked:** `assert df["timestamp"].notna().all()` and `assert df["timestamp"].is_monotonic_increasing`.

> **Transform 5:** `validate_epw_physical_ranges`
> - **What it changed:** Did not modify values; checked that temperature, RH, wind, direction, and radiation lie inside plausible ranges.
> - **Why this and not the alternative:** Because the selected EPW fields are already clean, we do not impute or clip primary climate values. We fail loudly if the data violates physical assumptions.
> - **Downstream effect:** Rule-engine confidence depends on physically valid primary climate fields.
> - **Reversibility:** Not applicable — validation only.
> - **Assertion that proves it worked:** temperature, RH, wind speed, wind direction, sky cover, and radiation range assertions all pass.

> **Transform 6:** `add_passive_design_features`
> - **What it changed:** Added `is_summer`, `is_cooling_season`, `is_night`, `cooling_degree_c_above_26`, `overheating_hour_proxy_26c`, `solar_radiation_total_wh_m2`, `wind_available_flag_1p5ms`, and `night_purge_candidate_flag`.
> - **Why this and not the alternative:** The project is a rule-based advisor, so the cleaned dataset should carry interpretable design indicators rather than opaque model features.
> - **Downstream effect:** Phase 4 strategy scoring can directly use these features for shading, night purge, thermal mass, and ventilation checks.
> - **Reversibility:** Yes — all derived columns are computed from preserved base fields.
> - **Assertion that proves it worked:** derived boolean columns contain only boolean values, and `cooling_degree_c_above_26 >= 0`.

> **Transform 7:** `format_final_schema`
> - **What it changed:** Ordered final columns, sorted by timestamp, reset index, and prepared the output for parquet.
> - **Why this and not the alternative:** Parquet preserves types and is more reliable than CSV for downstream reproducible analysis.
> - **Downstream effect:** Later components consume a stable schema rather than the original EPW text format.
> - **Reversibility:** Yes — raw EPW is unchanged and final schema is documented.
> - **Assertion that proves it worked:** `assert set(FINAL_COLUMNS).issubset(df.columns)` and `assert len(df_out) == 8760`.

---

## What we did NOT clean — and why

| Issue | Why we left it | What downstream needs to know |
|---|---|---|
| TMY month discontinuities | This is inherent to the TMY method, not an error | Do not use the file as a real chronological year or for multi-day event sequencing across month boundaries |
| Airport-vs-urban-core bias | Cannot be fixed from EPW alone | Apply thermal comfort zone / UHI correction later and disclose uncertainty |
| Wind speed at 10 m airport reference | Street-level wind requires morphology correction | Use ICGC Alçades + OSM canyon ratio to reduce wind confidence in deep canyons |
| Heatwave absence | TMY is typical, not extreme | Do not use for heatwave or future-climate resilience claims |

---

## Cumulative effect — raw vs cleaned

Of 8,760 raw hourly EPW records, 8,760 survived cleaning (100% retained). The cleaning preserved the full synthetic annual climate sequence while reducing the file to the variables needed for passive strategy evaluation. The cleaned dataset is suitable for screening-level climate indicators: overheating proxy, cooling degree hours, wind availability, solar exposure, and night-purge potential. It is **not** suitable for street-level microclimate claims, heatwave risk assessment, or real historical time-series analysis.

---

## Sign-off

- [ ] `python src/clean_data.py` produces `data/processed/barcelona-epw-tmyx-clean.parquet`
- [ ] Re-running on the same input produces an identical parquet
- [ ] `01-data-profiling.ipynb` re-run on the cleaned data shows anomalies resolved or documented
- [ ] All assertions in `assert_clean_invariants` pass
- [x] This log has one entry per transform

**Cleaned by:** Passive Design Advisor team  
**Reviewed by another team:** [name] on [date]  
**Reviewer notes:** [fill after peer review]
