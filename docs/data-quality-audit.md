# Data Quality Audit — Barcelona TMYx EPW Weather File

> Honest assessment of the dataset's fitness for YOUR brief, based on what
> profiling revealed. Not a generic data-quality report — specifically
> answers "can we use this for what we're trying to do?"
>
> Save as `docs/data-quality-audit-epw.md` in your repo.

---

## Dataset under audit

- **Dataset:** Barcelona El Prat Airport — TMYx Typical Meteorological Year (EPW)
- **File:** `ESP_CT_Barcelona-El_Prat_AP_081810_TMYx.epw`
- **Profiling performed by:** Passive Design Advisor team
- **Date:** 2025-05-17

---

## Gaps

### Temporal gaps

No missing hours — all 8,760 hourly rows are present, with correct counts per month (e.g. January = 744, February = 672, etc.). All months confirmed complete.

However, the TMY construction introduces a structural temporal discontinuity: each month is drawn from a different source year (Jan=1999, Feb=1989, Mar=2011, Apr=2009, May=2016, Jun=1996, Jul=2014, Aug=2008, Sep=2009, Oct=1999, Nov=1987, Dec=2020). This means the file does not represent a continuous real year — there are 11 artificial seams at month boundaries where atmospheric conditions may jump abruptly. This is expected and intentional in TMY design, but means the file cannot be used for sequential multi-day analysis that spans month boundaries.

### Spatial gaps

The dataset covers a single point — Barcelona El Prat Airport (WMO 081810, lat 41.293°N, lon 2.070°E). It provides no spatial variation across the city. All intra-urban microclimate differences (Eixample vs. Barceloneta vs. Gràcia) are invisible to this dataset.

### Field-level gaps

| Field | % missing / flagged | Pattern | Implication |
|---|---|---|---|
| Dry bulb temperature | 0% | None | Clean — use directly |
| Relative humidity | 0% | None | Clean — use directly |
| GHI | 0% | None — but see anomaly #1 | Investigate before use |
| DNI | 0% | None | Clean — use directly |
| DHI | 43.6% flagged (3,818 rows) | Daytime hours only — see anomaly #2 | DHI is illuminance, not irradiance — not a gap |
| Wind speed | 0% | None | Clean — use directly |
| Wind direction | 0% | But only 11 unique values — see anomaly #3 | Directional resolution is very coarse |
| Atmospheric pressure | 0.4% (34 rows) | No detectable pattern | Negligible; pressure not used in pipeline |
| Aerosol optical depth | 0% flagged numerically | Values appear constant — not used | Not relevant to our pipeline |
| Albedo | 0% flagged numerically | Values appear constant — not used | Not relevant to our pipeline |

---

## Anomalies found during profiling

| # | Anomaly | Diagnosis | Action taken |
|---|---|---|---|
| 1 | GHI column: min = 214, mean = 326, **no zero values in 8,760 rows** — including night hours | GHI is the **monthly total horizontal irradiance** column in the EPW column order, not the hourly value. What appears to be "GHI" at position 13 is actually the extraterrestrial horizontal radiation (ETR), which is a theoretical maximum and is non-zero even at night. True hourly GHI is at column index 21 (field name `ghillum` — global horizontal illuminance in lux, not Wh/m²). The actual radiation field (Wh/m²) with realistic zero-at-night behaviour is `etrn` (extraterrestrial normal) vs actual measured GHI. **The EPW column mapping is offset from what a naive parser would expect.** | Use a validated EPW reader (pvlib, Ladybug) that applies the correct EPW column specification. Do not parse by position manually. Verified: pvlib's `read_epw()` correctly maps all radiation fields. |
| 2 | DHI column (position 17) has 3,818 rows with values ranging from 10,000–99,000 — far above expected Wh/m² range for diffuse irradiance | These values are in **lux (illuminance)**, not Wh/m². Position 17 in the EPW is diffuse horizontal **illuminance** (lux), not diffuse horizontal **irradiance** (Wh/m²). The actual DHI in Wh/m² is at a different position. This is a column-labelling confusion, not a data error. | Use pvlib or Ladybug EPW reader to extract radiation by field name, not column index. |
| 3 | Wind direction has only **11 unique values** (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10) rather than the expected 0–360° continuous range | Wind direction is stored in **tens of degrees** (i.e. multiply by 10° to get compass bearing). Value `3` = 30° (NNE), `9` = 90° (E), `0` = calm. This is standard WMO encoding for ISD data and is correctly handled by pvlib. The dominant directions are: `3` (NNE/NE, 37% of hours), `5` (SW, 19%), `9` (W, 16%). This confirms the known Barcelona wind regime — sea breeze from SW/SSW in summer, NW Tramuntana in winter. | Multiply raw values by 10 to obtain degrees if parsing manually. pvlib handles this automatically. No data quality issue — encoding artifact only. |
| 4 | Atmospheric pressure: 34 rows have values ≥ 99,900 Pa | Spot check shows these are all valid readings around 100,000–104,000 Pa. The 99,900 threshold used in our profiling script was incorrectly set — these are not missing values. The EPW missing flag for pressure would be 999900. | No action needed — pressure field is complete. Script threshold corrected. |
| 5 | Night purge potential is very limited: only **64 summer night hours** (after 20:00) below 20°C and **123 hours** below 22°C | This is not a data anomaly — it is a genuine climate characteristic of Barcelona. Summer nights are warm and humid due to sea influence; the city rarely cools below 20°C after sunset in June–August. This directly constrains the night purge strategy score. | Document in rule engine: night purge PARTIAL or LOW for most Barcelona sites. Threshold may need to be raised to 24°C for Mediterranean context per Santamouris literature. |

---

## Bias check

- **Selection bias:** The TMY algorithm selects months that are *typical*, not recent or extreme. Years with heatwaves (2003, 2019, 2022) are explicitly excluded if they are atypical. This biases the file toward cooler summer conditions than an architect designing for the next 50 years should assume.

- **Measurement bias:** The airport station sits in an open, peri-urban coastal location. It systematically underestimates: (a) nighttime temperatures in the dense urban core by ~1–2°C due to lower urban heat island intensity; (b) daytime solar absorption, as urban surfaces have lower albedo than the airport environment; (c) wind sheltering in deep street canyons (H/W > 1), where actual wind speeds at 2 m height can be 40–60% of the 10 m airport anemometer reading.

- **Coverage bias:** Single-station — no spatial variation. The entire city of Barcelona (101 km², 1.6 million people) is represented by one point 12 km from the urban centre.

- **Temporal drift / non-stationarity:** The TMY base period (1973–2023) spans 51 years of warming. The file does not represent a stationary climate — it blends observations from the relatively cool 1980s with more recent warmer years. For long-lived buildings, it underestimates future climate loads. The 2011–2025 TMYx release (now available on climate.onebuilding.org) would be more representative of near-future conditions and should be considered as an update.

- **Label bias:** Not applicable — no labels or classifications in this dataset.

---

## Fitness for OUR brief

- **Sub-question: Which climate conditions most strongly determine whether passive design can meet adaptive thermal comfort standards?**
  - **Answer:** Partial
  - **Why:** The EPW provides accurate seasonal temperature, humidity, and solar radiation patterns for Barcelona, which are sufficient to evaluate shading, thermal mass, and ventilation potential at the neighbourhood level. However, the airport-vs-urban-core bias means the file will *underestimate* overheating hours in dense central districts. The July diurnal swing of 6.5°C is likely lower in the urban core (urban nights are warmer, not cooler), making the file optimistic about night purge potential compared to reality.

- **Sub-question: Which passive strategies are physically actionable given a specific building's geometry and urban context?**
  - **Answer:** Partial
  - **Why:** Wind speed and direction are present and usable for cross-ventilation checks. Solar radiation is present for shading geometry calculations (via pvlib sun position + DNI/GHI). However, wind speed at 10 m airport elevation is not representative of street-level wind in deep canyons — a canyon correction factor is needed. The EPW alone cannot provide site-specific wind data; it gives city-level prevailing wind patterns only.

- **Sub-question: Can the tool produce a ranked scorecard of passive strategies?**
  - **Answer:** Yes
  - **Why:** All variables needed for the rule engine thresholds are present and clean: dry bulb temperature (diurnal swing, cooling degree hours, running mean for EN 16798-1 comfort model), GHI/DNI for solar exposure, wind speed for ventilation checks, relative humidity for comfort bounds. The EPW is fit for this purpose as the primary climate input.

---

## Decisions

- **What we WILL use this dataset for:**
  - Computing monthly dry bulb temperature statistics (mean, max, diurnal swing) for thermal mass and night purge checks
  - Computing annual and summer cooling degree hours above 26°C for overheating risk assessment
  - Deriving the running mean outdoor temperature for the EN 16798-1 adaptive comfort model
  - Generating sun position angles (via pvlib) using the site latitude/longitude from the EPW header
  - Providing prevailing wind direction and monthly mean wind speed for cross-ventilation orientation checks
  - Confirming Barcelona's climate falls in the applicability range of EN 16798-1 naturally ventilated building model

- **What we will NOT use this dataset for:**
  1. **Precise wind speed at street level** — the 10 m airport anemometer reading overestimates actual canyon wind speeds in dense urban blocks. All wind-speed-dependent checks (cross-ventilation, night purge) will apply a conservative canyon correction factor of 0.5–0.6× for sites with H/W ratio > 1, documented in the tool output.
  2. **Heatwave risk assessment or worst-case design scenarios** — the TMY construction excludes extreme years by design. If a future version of the tool needs to evaluate resilience under climate extremes or future warming scenarios, a different input file (e.g. a design summer year or a +2°C morphed EPW) should be used instead.
  3. **Night purge strategy impact above MEDIUM** — the 6.5°C July diurnal swing is below the 10°C threshold for "high" effectiveness. The rule engine will cap night purge impact at MEDIUM for all Barcelona sites unless a site-specific measurement confirms otherwise.

- **What additional source(s) we'd need to fill the gaps:**
  - **UHI temperature correction:** Dataset 4 (`confort_termic_od.gpkg`) provides a zone-level thermal comfort classification that partially compensates for the airport-vs-urban bias. A future improvement would apply a +1.5°C delta-T to nighttime summer dry bulb for zones with `gridcode` 5–6.
  - **Street-level wind:** No open dataset provides this directly for Barcelona. The OSM street network (dataset 2) + ICGC building heights (dataset 3) can be used to compute H/W ratio and apply a literature-based canyon correction factor.
  - **Future climate:** The 2011–2025 TMYx from climate.onebuilding.org should be downloaded and substituted for the 2004–2018 base file to better represent near-future conditions.

---

## Implications for the brief

The audit does not force a change to the problem brief. The EPW is fit for purpose as a screening-level passive design advisor, provided two things are documented clearly in the tool output:

1. All strategy impact scores are derived from airport climate data and may underestimate overheating risk in dense central Barcelona by 1–2°C — scores for high-density sites (thermal comfort gridcode 5–6) should be interpreted as conservative lower bounds.
2. Night purge ventilation and thermal mass scores are MEDIUM rather than HIGH for Barcelona's typical climate, consistent with the low diurnal swing — this is a climate fact, not a tool limitation.

No change to `problem-brief.md` required. Flag both points in the tool's output UI.

---

## Per-team-member contributions

### [Gaelle Habib]

### [Chun-Chun Chang]

### [Nithik Vairamuthu]

### [Vimal TN]
