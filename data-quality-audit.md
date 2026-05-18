# Data Quality Audit — Open-Meteo Historical Weather Inputs

> Honest assessment of the dataset's fitness for the Barcelona passive-design brief. This is not a generic data-quality report; it answers whether the climate inputs are usable for the scorecard logic.

---

## Dataset under audit

- **Dataset:** Open-Meteo historical weather inputs for Barcelona (temperature, humidity, wind, solar radiation, sky-condition proxy)
- **Profiling notebook:** `notebooks/01-data-profiling.ipynb`
- **Audit performed by:** Gaelle Habib, Chun-Chun Chang, Nithik Vairamuthu, Vimal TN
- **Date:** 2026-05-04

---

## Gaps

### Temporal gaps

The source is suitable for hourly climate logic, but two timing issues matter for the project: timezone alignment and daylight-saving transitions. The data needs to be normalized to Barcelona local time before it can be used in façade-by-hour checks, otherwise the wind and solar logic will be shifted by one hour in parts of the year.

### Spatial gaps

The dataset covers Barcelona at city scale, but it does not resolve street-canyon variation or courtyard microclimates. That means it can support a building-level scorecard, but not a room-by-room or block-shadow simulation.

### Field-level gaps

| Field | % missing | Pattern of missingness | Implication |
|---|---|---|---|
| Sky condition / cloud proxy | Low to medium | Sometimes omitted or derived from a coarser weather source | Daylighting and solar-gain logic needs a fallback assumption when cloud cover is unavailable. |
| Wind direction | Low | May be sparse in calm periods or noisy near calm thresholds | Cross-ventilation checks should use prevailing-direction summaries, not raw hour-by-hour direction alone. |
| Solar radiation by direction | Low | Usually available, but orientation-specific derivation is modeled rather than directly observed | Facade-specific output is a calculation, not a measured fact. |

---

## Anomalies found during profiling

| # | Anomaly | Diagnosis | Action taken |
|---|---|---|---|
| 1 | Duplicate or shifted hours around DST | Weather timestamps may be stored in UTC while the user expects local Barcelona time | Normalize to local time before aggregating daily design-day summaries. |
| 2 | Calm-wind hours with unstable direction | Wind direction can become meaningless when speed is near zero | Use speed thresholds before interpreting direction in the ventilation logic. |
| 3 | Extreme solar values in a few hours | Likely summer clear-sky peaks or unit conversion issues | Clamp units and compare against expected Barcelona summer ranges. |
| 4 | Missing sky-condition proxy in some rows | Cloudiness is not always exposed directly by the endpoint | Fall back to irradiance-based assumptions for daylighting checks. |
| 5 | Edge-hour mismatch at day boundaries | Hourly bins can shift when joining climate to geometry summaries | Aggregate after timezone correction, not before. |

---

## Bias check

- **Selection bias:** Low. The climate source is not neighborhood-skewed, but it is still a model-based representation rather than a sensor network.
- **Measurement bias:** Medium. Open-Meteo climate values depend on the underlying weather/reanalysis product and can smooth local extremes.
- **Coverage bias:** Low to medium. City coverage is good, but the dataset does not capture microclimate features like canyon shading or courtyard effects.
- **Temporal drift / non-stationarity:** Medium. The climate logic is time-sensitive, so annual variation and heatwave years must be treated separately.
- **Label bias** *(if applicable):* Not applicable. This dataset has no human-labeled target variable.

---

## Fitness for OUR brief

- **Sub-question 1:** What climate inputs matter, and how do they affect the scorecard?
  - **Answer:** Yes
  - **Why:** Hourly temperature, humidity, wind, radiation, and sky conditions are exactly the variables needed for the strategy checks.

- **Sub-question 2:** What climate thresholds make a passive strategy high, medium, or low impact?
  - **Answer:** Partial
  - **Why:** The dataset can supply the climate side of the rule, but the thresholds still come from standards and design literature.

- **Sub-question 3:** Can the dataset tell us whether the building is physically actionable for shading or ventilation?
  - **Answer:** No
  - **Why:** That depends on geometry and urban context, which are separate inputs.

---

## Decisions

- **What we WILL use this dataset for:**
  - Climate baseline for summer overheating screening.
  - Solar, wind, humidity, and temperature inputs for the precondition and impact checks.

- **What we will NOT use this dataset for:** *(at least 2 specific things)*
  1. Room-level comfort prediction without geometry and indoor measurements.
  2. Street-canyon wind or shadow simulation on its own.

- **What additional source(s) we'd need to fill the gaps:**
  - Barcelona cadastre / 3D geometry layer for façade and roof inputs.
  - Urban morphology / city context layer for surrounding heights, canyon geometry, and open-space distance.
  - A comfort benchmark source such as EN 15251 or ASHRAE 55 for the final comparison logic.

---

## Implications for the brief

Yes. The brief should stay focused on a calculation framework instead of a predictive comfort model. That change is documented in [problem-brief-v2.md](problem-brief-v2.md).

---

## Per-team-member contributions

### Gaelle Habib

Gaelle reviewed the audit framing against the project brief and checked that the climate inputs were being used for design-stage scoring rather than for an indoor prediction claim.

### Chun-Chun Chang

Chun-Chun checked the source logic and helped align the audit with the data inventory so the climate layer, geometry layer, and benchmark layer each have a clear role.

### Nithik Vairamuthu

Nithik focused on the profiling structure, especially the field-level checks and anomaly list, so the notebook can later confirm or refine these provisional findings.

### Vimal TN

Vimal reviewed the audit against the system sketch to make sure the limitations are visible in the final scorecard and do not get hidden behind a neat-looking recommendation table.
