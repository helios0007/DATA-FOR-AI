# 02 · Data Cleaning Notebook — Scaffold

> Copy each cell into `notebooks/02-data-cleaning.ipynb`.
>
> Primary dataset: **Barcelona EPW — TMYx Weather File**.  
> ICGC Alçades, OSM, thermal comfort zones, and vegetation layers are supporting datasets, not the primary Session 3 cleaning target.

---

## Cell 1 — Markdown: title & purpose

```markdown
# Data Cleaning — Barcelona EPW / TMYx Weather File

**Purpose:** clean and structure the primary EPW climate dataset for the Passive Design Advisor.

**Project role:** primary climate input for overheating, adaptive comfort, shading, natural ventilation, night-purge, and thermal-mass checks.

**Input:** `data/raw/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw`  
**Output:** `data/processed/barcelona-epw-tmyx-clean.parquet`  
**Cleaning log:** `docs/data-cleaning-log.md`

This notebook is exploratory. Stable logic is promoted to `src/clean_data.py`.
```

---

## Cell 2 — Imports & deterministic config

```python
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

RAW_PATH = Path("../data/raw/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw")
OUT_PATH = Path("../data/processed/barcelona-epw-tmyx-clean.parquet")
RANDOM_SEED = 42

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
pd.set_option("display.max_columns", 80)
pd.set_option("display.precision", 4)
np.random.seed(RANDOM_SEED)
```

---

## Cell 3 — EPW column schema

```python
EPW_COLUMNS = [
    "source_year", "month", "day", "hour", "minute",
    "data_source_uncertainty",
    "dry_bulb_temp_c", "dew_point_temp_c", "relative_humidity_pct",
    "atmospheric_pressure_pa",
    "extraterrestrial_horizontal_radiation_wh_m2",
    "extraterrestrial_direct_normal_radiation_wh_m2",
    "horizontal_infrared_radiation_wh_m2",
    "global_horizontal_radiation_wh_m2",
    "direct_normal_radiation_wh_m2",
    "diffuse_horizontal_radiation_wh_m2",
    "global_horizontal_illuminance_lux",
    "direct_normal_illuminance_lux",
    "diffuse_horizontal_illuminance_lux",
    "zenith_luminance_cd_m2",
    "wind_direction_deg",
    "wind_speed_m_s",
    "total_sky_cover_tenths",
    "opaque_sky_cover_tenths",
    "visibility_km",
    "ceiling_height_m",
    "present_weather_observation",
    "present_weather_codes",
    "precipitable_water_mm",
    "aerosol_optical_depth_thousandths",
    "snow_depth_cm",
    "days_since_last_snowfall",
    "albedo",
    "liquid_precipitation_depth_mm",
    "liquid_precipitation_quantity_hr",
]
```

---

## Cell 4 — Load raw EPW + initial shape check

```python
df_raw = pd.read_csv(RAW_PATH, skiprows=8, header=None, names=EPW_COLUMNS)
print(f"Raw shape: {df_raw.shape}")
assert len(df_raw) == 8760, "EPW should contain 8,760 hourly rows."

df = df_raw.copy()
df.head()
```

---

# Task 1 — Select

## Cell 5 — Selection plan

```markdown
## Task 1: Select

- **Rows kept:** all 8,760 hourly records.
- **Columns kept:** date fields, temperature, humidity, solar radiation, wind, and sky cover.
- **Time window:** full synthetic TMY year.
- **Spatial extent:** single station point — Barcelona El Prat Airport.
```

## Cell 6 — Apply column selection

```python
COLS_KEEP = [
    "source_year", "month", "day", "hour",
    "dry_bulb_temp_c", "dew_point_temp_c", "relative_humidity_pct",
    "global_horizontal_radiation_wh_m2",
    "direct_normal_radiation_wh_m2",
    "diffuse_horizontal_radiation_wh_m2",
    "wind_direction_deg", "wind_speed_m_s",
    "total_sky_cover_tenths",
    "opaque_sky_cover_tenths",
]

df = df[COLS_KEEP].copy()
print(f"After selection: {df.shape}")
```

---

# Task 2 — Clean

## Cell 7 — Cleaning plan

```markdown
## Task 2: Clean

Main decisions:
- Use explicit EPW field names rather than naive column positions.
- Confirm 8,760 hourly records.
- Coerce physical variables to numeric.
- Preserve `source_year` and raw EPW hour for traceability.
- Construct a deterministic synthetic timestamp for sorting and plotting.
```

## Cell 8 — Type coercion

```python
NUMERIC_COLS = COLS_KEEP

for col in NUMERIC_COLS:
    df[col] = pd.to_numeric(df[col], errors="coerce")

missing = df[NUMERIC_COLS].isna().sum().sort_values(ascending=False)
print(missing[missing > 0])
assert df[["month", "day", "hour"]].notna().all().all()
```

## Cell 9 — Construct deterministic timestamp

```python
df["hour_raw_epw"] = df["hour"].astype("int16")
df["hour_of_day"] = (df["hour_raw_epw"] - 1).astype("int8")

df["timestamp"] = pd.to_datetime(
    {
        "year": 2025,
        "month": df["month"].astype(int),
        "day": df["day"].astype(int),
        "hour": df["hour_of_day"].astype(int),
    },
    errors="coerce",
)

assert df["timestamp"].notna().all()
df = df.sort_values("timestamp").reset_index(drop=True)
assert df["timestamp"].is_monotonic_increasing
```

## Cell 10 — Physical range assertions

```python
assert df["dry_bulb_temp_c"].between(-20, 50).all()
assert df["dew_point_temp_c"].between(-30, 35).all()
assert df["relative_humidity_pct"].between(0, 100).all()
assert df["wind_speed_m_s"].between(0, 60).all()
assert df["wind_direction_deg"].between(0, 360).all()

for col in [
    "global_horizontal_radiation_wh_m2",
    "direct_normal_radiation_wh_m2",
    "diffuse_horizontal_radiation_wh_m2",
]:
    assert (df[col] >= 0).all(), f"{col} contains negative values."
```

## Cell 11 — Missing-value decision

```python
miss_frac = df.isna().mean().sort_values(ascending=False)
print(miss_frac[miss_frac > 0])

required = [
    "dry_bulb_temp_c",
    "relative_humidity_pct",
    "global_horizontal_radiation_wh_m2",
    "direct_normal_radiation_wh_m2",
    "diffuse_horizontal_radiation_wh_m2",
    "wind_speed_m_s",
    "wind_direction_deg",
]

assert df[required].notna().all().all()
```

---

# Task 3 — Construct

## Cell 12 — Passive-design derived features

```python
df["month"] = df["month"].astype("int8")
df["day"] = df["day"].astype("int8")

df["is_summer"] = df["month"].isin([6, 7, 8])
df["is_cooling_season"] = df["month"].isin([5, 6, 7, 8, 9])
df["is_night"] = (df["hour_of_day"] >= 20) | (df["hour_of_day"] <= 6)

df["cooling_degree_c_above_26"] = (df["dry_bulb_temp_c"] - 26).clip(lower=0)
df["overheating_hour_proxy_26c"] = df["dry_bulb_temp_c"] > 26

df["solar_radiation_total_wh_m2"] = (
    df["global_horizontal_radiation_wh_m2"]
    + df["direct_normal_radiation_wh_m2"]
    + df["diffuse_horizontal_radiation_wh_m2"]
)

df["wind_available_flag_1p5ms"] = df["wind_speed_m_s"] >= 1.5
df["night_purge_candidate_flag"] = (
    df["is_night"] & df["is_summer"] & (df["dry_bulb_temp_c"] <= 22)
)
```

## Cell 13 — Monthly diagnostic summaries

```python
monthly_summary = (
    df.groupby("month")
    .agg(
        mean_temp_c=("dry_bulb_temp_c", "mean"),
        max_temp_c=("dry_bulb_temp_c", "max"),
        p95_temp_c=("dry_bulb_temp_c", lambda s: s.quantile(0.95)),
        mean_wind_speed_m_s=("wind_speed_m_s", "mean"),
        cooling_degree_hours_26c=("cooling_degree_c_above_26", "sum"),
        overheating_hours_26c=("overheating_hour_proxy_26c", "sum"),
        night_purge_candidate_hours=("night_purge_candidate_flag", "sum"),
    )
)

monthly_summary
```

---

# Task 4 — Integrate

## Cell 14 — Integration note

```markdown
## Task 4: Integrate

No spatial join is performed in this primary EPW cleaning notebook.

Later stages integrate:
- ICGC Alçades / OSM morphology for obstruction and canyon correction.
- Open Data BCN thermal comfort zones for urban heat adjustment.
- Copernicus Street Tree Layer for vegetation context.
```

---

# Task 5 — Format

## Cell 15 — Final schema check

```python
FINAL_COLS = [
    "timestamp", "source_year", "month", "day", "hour_raw_epw", "hour_of_day",
    "dry_bulb_temp_c", "dew_point_temp_c", "relative_humidity_pct",
    "global_horizontal_radiation_wh_m2",
    "direct_normal_radiation_wh_m2",
    "diffuse_horizontal_radiation_wh_m2",
    "wind_direction_deg", "wind_speed_m_s",
    "total_sky_cover_tenths", "opaque_sky_cover_tenths",
    "is_summer", "is_cooling_season", "is_night",
    "cooling_degree_c_above_26", "overheating_hour_proxy_26c",
    "solar_radiation_total_wh_m2", "wind_available_flag_1p5ms",
    "night_purge_candidate_flag",
]

assert set(FINAL_COLS).issubset(df.columns)
df_out = df[FINAL_COLS].sort_values("timestamp").reset_index(drop=True)
assert len(df_out) == 8760
df_out.dtypes
```

## Cell 16 — Write parquet output

```python
df_out.to_parquet(OUT_PATH, index=False)
print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")
```

---

# Task 6 — Verify

## Cell 17 — Temperature distribution

```python
fig, ax = plt.subplots(figsize=(10, 5))
ax.hist(df_out["dry_bulb_temp_c"], bins=50)
ax.set_xlabel("Dry bulb temperature (°C)")
ax.set_ylabel("Hours")
ax.set_title("Barcelona EPW dry bulb temperature distribution")
plt.tight_layout()
plt.show()
```

## Cell 18 — Monthly overheating hours

```python
fig, ax = plt.subplots(figsize=(10, 5))
monthly_summary["overheating_hours_26c"].plot(kind="bar", ax=ax)
ax.set_xlabel("Month")
ax.set_ylabel("Hours above 26°C")
ax.set_title("Monthly overheating-hour proxy")
plt.tight_layout()
plt.show()
```

## Cell 19 — What changed

```markdown
## What did cleaning change?

1. **Read EPW with explicit schema** — prevented radiation / illuminance confusion.
2. **Selected project-relevant fields** — reduced EPW to variables used by the rule engine.
3. **Constructed synthetic timestamp** — ordered hourly records while preserving TMY source year.
4. **Validated physical ranges** — checked temperature, humidity, wind, and radiation.
5. **Derived passive-design indicators** — added overheating, cooling-season, wind, and night-purge flags.

**Total rows raw → cleaned:** 8,760 → 8,760 (100% retained)
```

---

# Task 7 — Bridge to the module

## Cell 20 — What gets promoted

```markdown
Promote:
- `read_epw`
- `select_epw_fields`
- `coerce_epw_numeric_fields`
- `construct_epw_timestamp`
- `validate_epw_physical_ranges`
- `add_passive_design_features`
- `format_final_schema`
- `clean_epw_dataset`
```
