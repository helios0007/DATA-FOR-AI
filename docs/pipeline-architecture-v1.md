# Pipeline Architecture v1 — Passive Design Advisor: Barcelona 2025

> This file evolves `system-sketch-v0.md` into a real pipeline now that the primary data cleaning step is code-backed.
>
> Source of truth for Session 3: **EPW climate cleaning is implemented; urban morphology integration remains a later component.**

---

## What changed since v0

In Session 2, the system sketch described climate, geometry, morphology, rules, and output at a high level. In Session 3, the first implemented box is the cleaning pipeline for the **primary dataset: Barcelona EPW / TMYx Weather File**.

The ICGC Alçades dataset is not the overall primary dataset. It is a supporting morphology source used later for obstruction, canyon, and wind-sheltering indicators.

---

## The diagram

```mermaid
flowchart LR
    subgraph raw [Raw inputs]
        R1[Barcelona EPW / TMYx<br/>data/raw/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw]
        R2[ICGC Alçades building heights<br/>(supporting morphology · planned)]
        R3[OSM buildings + roads<br/>(supporting footprint/network · planned)]
        R4[Open Data BCN thermal comfort zones<br/>(UHI/context modifier · planned)]
        R5[Passive design standards / papers<br/>(RAG + thresholds · planned)]
    end

    subgraph clean [Phase 3 · implemented cleaning]
        C1[read_epw<br/>src/clean_data.py]
        C2[select_epw_fields<br/>src/clean_data.py]
        C3[coerce_epw_numeric_fields<br/>src/clean_data.py]
        C4[construct_epw_timestamp<br/>src/clean_data.py]
        C5[validate_epw_physical_ranges<br/>src/clean_data.py]
        C6[add_passive_design_features<br/>src/clean_data.py]
        C7[format_final_schema<br/>src/clean_data.py]
    end

    subgraph processed [Processed]
        P1[barcelona-epw-tmyx-clean.parquet<br/>data/processed/]
    end

    subgraph future [Future · Phase 4-7]
        F1[rule-based strategy scorer<br/>(planned · Session 4)]
        F2[urban-context adjustment<br/>(planned · Session 4-5)]
        F3[RAG-supported explanation<br/>(planned · Session 5-6)]
        F4[decision-facing scorecard<br/>(planned · Session 7)]
    end

    R1 --> C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> C7 --> P1
    P1 --> F1
    R2 -.-> F2
    R3 -.-> F2
    R4 -.-> F2
    R5 -.-> F3
    F1 --> F2 --> F3 --> F4
```

---

## Components — implemented, Phase 3

### `read_epw`

- **File:** `src/clean_data.py`
- **Input contract:** EPW file at `data/raw/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw`
- **Output contract:** `pd.DataFrame` with 8,760 rows and official EPW columns
- **Failure mode:** raises if the file is missing or row count is not 8,760
- **Tests / assertions:** `assert len(df_raw) == 8760`
- **Cleaning log entry:** Transform 1 in `docs/data-cleaning-log.md`

### `select_epw_fields`

- **File:** `src/clean_data.py`
- **Input contract:** raw EPW dataframe with 35 EPW columns
- **Output contract:** dataframe containing only fields needed by the Passive Design Advisor
- **Failure mode:** raises `ValueError` if expected EPW fields are missing
- **Tests / assertions:** selected columns subset check
- **Cleaning log entry:** Transform 2

### `coerce_epw_numeric_fields`

- **File:** `src/clean_data.py`
- **Input contract:** selected EPW dataframe
- **Output contract:** selected numeric climate fields converted to numeric dtypes
- **Failure mode:** raises if required numeric fields become null
- **Tests / assertions:** required fields not null after coercion
- **Cleaning log entry:** Transform 3

### `construct_epw_timestamp`

- **File:** `src/clean_data.py`
- **Input contract:** month/day/hour fields where EPW hour is 1–24
- **Output contract:** dataframe with `hour_raw_epw`, `hour_of_day`, and synthetic `timestamp`
- **Failure mode:** raises if timestamp construction fails
- **Tests / assertions:** no null timestamps; monotonic increasing order
- **Cleaning log entry:** Transform 4

### `validate_epw_physical_ranges`

- **File:** `src/clean_data.py`
- **Input contract:** cleaned numeric climate dataframe
- **Output contract:** same dataframe; validation only
- **Failure mode:** raises if temperature, humidity, wind, direction, or radiation fields violate plausible ranges
- **Tests / assertions:** physical range assertions
- **Cleaning log entry:** Transform 5

### `add_passive_design_features`

- **File:** `src/clean_data.py`
- **Input contract:** validated climate dataframe
- **Output contract:** dataframe with interpretable passive-design columns
- **Failure mode:** raises if derived columns are missing or invalid
- **Tests / assertions:** boolean indicator checks and non-negative cooling-degree values
- **Cleaning log entry:** Transform 6

### `format_final_schema`

- **File:** `src/clean_data.py`
- **Input contract:** dataframe with base and derived columns
- **Output contract:** final ordered schema with 8,760 rows
- **Failure mode:** raises if final columns are missing
- **Tests / assertions:** final schema subset and row count
- **Cleaning log entry:** Transform 7

---

## Components — planned, Phase 4–7

| Component | Lands in | One-line role |
|---|---|---|
| Rule-based strategy scorer | Session 4 | Converts cleaned EPW climate indicators into YES / PARTIAL / NO passive-strategy precondition checks |
| Urban morphology processor | Session 4–5 | Uses ICGC Alçades + OSM to compute obstruction, canyon ratio, roof exposure, and wind-sheltering corrections |
| UHI / thermal comfort zone modifier | Session 4–5 | Adjusts overheating confidence using Barcelona thermal comfort zone lookup |
| RAG-supported explanation module | Session 5–6 | Retrieves passive-design literature and standards to explain why each score was assigned |
| Failure gallery | Session 6 | Documents cases where the rule system is weak or misleading |
| Decision-facing scorecard | Session 7 | Shows ranked passive strategies, input evidence, confidence, and limitations to the architect |

---

## The contracts

### `data/processed/barcelona-epw-tmyx-clean.parquet` schema

| Column | Type | Units | Source | Allowed range | Description |
|---|---|---|---|---|---|
| `timestamp` | datetime64 | synthetic local index | derived | 2025-01-01 to 2025-12-31 | Ordering timestamp only; not a real historical year |
| `source_year` | int | year | EPW | 1973–2023 expected | Historical source year for each TMY hour |
| `month` | int8 | month | EPW | 1–12 | Month of TMY record |
| `day` | int8 | day | EPW | 1–31 | Day of month |
| `hour_raw_epw` | int8 | hour | EPW | 1–24 | Original EPW hour field |
| `hour_of_day` | int8 | hour | derived | 0–23 | Converted hour used in analysis |
| `dry_bulb_temp_c` | float64 | °C | EPW | -20 to 50 | Outdoor dry bulb temperature |
| `dew_point_temp_c` | float64 | °C | EPW | -30 to 35 | Dew point temperature |
| `relative_humidity_pct` | float64 | % | EPW | 0–100 | Relative humidity |
| `global_horizontal_radiation_wh_m2` | float64 | Wh/m² | EPW | >= 0 | Horizontal global solar radiation |
| `direct_normal_radiation_wh_m2` | float64 | Wh/m² | EPW | >= 0 | Direct solar radiation |
| `diffuse_horizontal_radiation_wh_m2` | float64 | Wh/m² | EPW | >= 0 | Diffuse solar radiation |
| `wind_direction_deg` | float64 | degrees | EPW | 0–360 | Meteorological wind direction |
| `wind_speed_m_s` | float64 | m/s | EPW | 0–60 | Wind speed at reference station |
| `total_sky_cover_tenths` | float64 | tenths | EPW | 0–10 | Total sky cover |
| `opaque_sky_cover_tenths` | float64 | tenths | EPW | 0–10 | Opaque sky cover |
| `is_summer` | bool | — | derived | True/False | June–August flag |
| `is_cooling_season` | bool | — | derived | True/False | May–September flag |
| `is_night` | bool | — | derived | True/False | 20:00–06:00 flag |
| `cooling_degree_c_above_26` | float64 | °C-hour basis | derived | >= 0 | Temperature above 26°C threshold |
| `overheating_hour_proxy_26c` | bool | — | derived | True/False | Outdoor temperature above 26°C |
| `solar_radiation_total_wh_m2` | float64 | Wh/m² | derived | >= 0 | Sum of selected solar radiation fields |
| `wind_available_flag_1p5ms` | bool | — | derived | True/False | Wind speed >= 1.5 m/s |
| `night_purge_candidate_flag` | bool | — | derived | True/False | Summer night hour with outdoor temp <= 22°C |

---

## Open seams

- **Seam 1: EPW is airport climate, not central Barcelona microclimate**
  - **Why it is weak:** It can underestimate urban nighttime overheating and overestimate wind availability.
  - **Mitigation plan:** Apply thermal comfort zone modifier and morphology-based wind/canyon correction in later stages.

- **Seam 2: Strategy thresholds are not yet validated**
  - **Why it is weak:** Thresholds such as 26°C, 1.5 m/s, and 22°C are defensible starting points but need literature support.
  - **Mitigation plan:** Link each threshold to EN 16798-1 / ASHRAE 55 / passive-design literature in the RAG knowledge base.

- **Seam 3: No full energy simulation**
  - **Why it is weak:** Rule-based outputs are suitability checks, not indoor temperature predictions.
  - **Mitigation plan:** Label the output as a screening scorecard and avoid compliance / performance claims.

---

## Sign-off

**Drawn by:** Passive Design Advisor team  
**Last updated:** 2026-05-18  
**Diagram updated to match `src/clean_data.py`:** yes
