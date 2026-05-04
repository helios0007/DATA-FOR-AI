# Data Source Inventory

> Minimum 5 candidate datasets, each scored against the Dataset Assessment
> Rubric. Adopt only if total ≥ 10/14. Reject low scorers — that's the point
> of the rubric.

## How to use this file

1. List at least 5 candidate datasets. Don't stop at the first match — survey
   the landscape across the 6 categories (remote sensing optical, remote
   sensing thermal/radar, climate reanalysis, in-situ sensors, biodiversity,
   built environment).
2. For each, fill out provider, access method, and the rubric scoring table.
3. Write a one-paragraph plain-English description.
4. Issue a verdict: **Adopt / Reject / Investigate further.**
5. Only "Adopt" datasets get a full datasheet (`datasheets/<slug>.md`).

## The Dataset Assessment Rubric

| Axis | 0 | 1 | 2 |
|---|---|---|---|
| **Provenance** | Source unclear | Source documented | Documented + cited in peer-reviewed work |
| **Resolution match** | Coarser than decision unit | Roughly matches | ≥2× finer than decision unit |
| **Coverage** | Major gaps over our place/time | Minor gaps | Full coverage |
| **License** | Unclear / restrictive | Permissive with attribution | Public domain / CC0 |
| **Access reliability** | Manual scraping, fragile | API but rate-limited or unstable | Stable API or stable bulk download |
| **Bias clarity** | Unknown biases | Some documented | Biases fully documented + quantified |
| **Maintenance** | Stale, no updates | Updated irregularly | Actively maintained, contact available |

---

## 1. Open-Meteo Historical Weather API

- **Provider:** Open-Meteo GmbH / open meteo data services
- **Access method (URL / API / portal):** https://open-meteo.com/ and historical archive API
- **Category:** *(climate-reanalysis)*

### Rubric scoring (0–2 per axis)

| Axis | Score | Justification |
|---|---|---|
| Provenance | 1 | Source documented and widely used as an API wrapper for weather/reanalysis products. |
| Resolution match | 2 | Hourly climate variables align with the design-stage evaluation logic. |
| Coverage | 2 | Barcelona can be queried continuously over the target period. |
| License | 2 | Public access with attribution expectations; no restrictive local license for the API usage itself. |
| Access reliability | 2 | Stable API and documented endpoints. |
| Bias clarity | 1 | Biases depend on the underlying weather source; documented but not fully quantified in the API layer. |
| Maintenance | 2 | Actively maintained service. |
| **TOTAL** | **12/14** | |

### One-paragraph description


Open-Meteo provides hourly weather inputs for Barcelona that match the logic in the updated design: dry bulb temperature, humidity, wind speed and direction, solar radiation, and sky condition proxies. It is good for the rule-based checks in the scorecard, but it cannot by itself tell us whether a building actually meets comfort conditions indoors.

### Verdict

**Adopt.** It supports the climate side of the strategy logic at the right temporal resolution and is stable enough for a reproducible workflow.

---

## 2. Barcelona Cadastre / 3D Building Geometry

- **Provider:** Barcelona municipal cadastre and city open-data sources
- **Access method:** municipal GIS portal / downloadable layers
- **Category:** *(built-environment)*

### Rubric scoring

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | Official city source and building geometry is documented. |
| Resolution match | 2 | Building-scale geometry is the exact decision unit. |
| Coverage | 2 | Central Barcelona coverage is sufficient for the project scope. |
| License | 1 | Open but attribution / use constraints need checking per layer. |
| Access reliability | 1 | GIS portal access is usable but can require manual download or cleanup. |
| Bias clarity | 1 | Height and attribute bias are documented only partially. |
| Maintenance | 2 | Municipal data is maintained, though update cadence varies by layer. |
| **TOTAL** | **11/14** | |

### One-paragraph description

This layer gives the building footprint and geometry inputs needed for the passive-strategy checks: façade orientation, façade area, roof exposure, and the surrounding built form. It is the key source for deciding whether shading, ventilation, or green-roof strategies are physically actionable, but it should not be used as a precise structural survey.

### Verdict

**Adopt.** It is the best available geometry source for the scorecard logic.

---

## 3. PVGIS Solar Irradiation Service

- **Provider:** European Commission Joint Research Centre (JRC)
- **Access method:** https://re.jrc.ec.europa.eu/pvg_tools/en/
- **Category:** *(climate-reanalysis)*

### Rubric scoring

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | Official EU service with strong documentation and broad usage. |
| Resolution match | 2 | Orientation-specific solar values fit façade-level evaluation. |
| Coverage | 2 | Barcelona is fully covered by the service. |
| License | 1 | Public service, but terms need to be cited carefully. |
| Access reliability | 2 | Stable web service and downloadable outputs. |
| Bias clarity | 1 | Typical-year assumptions are known, but seasonality extremes are simplified. |
| Maintenance | 2 | Actively maintained by JRC. |
| **TOTAL** | **12/14** | |

### One-paragraph description

PVGIS gives the directional solar exposure needed to decide whether exterior shading is actually worth it on a specific façade and how much roof exposure matters for the green-roof case. It is a design-stage tool rather than a live-measurement source, so it should be treated as a calculation input, not a ground-truth comfort readout.

### Verdict

**Adopt.** It is directly useful for the solar side of the strategy logic.

---

## 4. Meteocat / AEMET Station Observations

- **Provider:** Servei Meteorològic de Catalunya / Agencia Estatal de Meteorología
- **Access method:** station portals / public climate records
- **Category:** *(in-situ-sensors)*

### Rubric scoring

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | Official meteorological agencies with documented stations. |
| Resolution match | 1 | Station data is useful but not always close to the building decision unit. |
| Coverage | 1 | Good for Barcelona generally, but station placement is uneven. |
| License | 1 | Access is public but reuse conditions vary by service. |
| Access reliability | 1 | Often portal-based or semi-manual rather than fully stable API. |
| Bias clarity | 1 | Station placement bias and urban heat island bias are only partly documented. |
| Maintenance | 2 | Actively maintained by the agencies. |
| **TOTAL** | **9/14** | |

### One-paragraph description

Station observations are useful as a validation layer for the climate inputs, especially for checking wind, humidity, and temperature patterns against local measurements. They are not fine enough to resolve every street canyon, so they should be used to confirm broad trends rather than to drive the final scorecard alone.

### Verdict

**Investigate further.** Useful for validation, but not strong enough to be the primary source.

---

## 5. Barcelona Urban Morphology / Open Space Context Layer

- **Provider:** Barcelona municipal open data and GIS layers
- **Access method:** municipal open-data portal / GIS download
- **Category:** *(built-environment)*

### Rubric scoring

| Axis | Score | Justification |
|---|---|---|
| Provenance | 1 | City data is documented, but layer lineage can be fragmented. |
| Resolution match | 2 | Block and street context is the right scale for canyon/shadow logic. |
| Coverage | 1 | Coverage may be partial across all needed morphology variables. |
| License | 1 | Usually open with attribution, but layer-specific terms need checking. |
| Access reliability | 1 | Portal access is usable but may require manual cleanup. |
| Bias clarity | 0 | Biases in completeness and accuracy are not yet well quantified. |
| Maintenance | 1 | Updated irregularly across different layers. |
| **TOTAL** | **7/14** | |

### One-paragraph description

This layer is the context layer for the recommendation logic: surrounding building heights, street-canyon geometry, distance to open space, and local urban heat island intensity. It is important for shading and cross-ventilation checks, but the quality of the derived indicators depends on how cleanly the city layers can be merged.

### Verdict

**Investigate further.** It is useful, but only if the geometry and context variables can be extracted reliably enough for the scorecard.

---

## Summary

- **Adopted:** Open-Meteo Historical Weather API; Barcelona Cadastre / 3D Building Geometry; PVGIS Solar Irradiation Service
- **Rejected:** None yet; the remaining sources are being held for validation rather than dropped.
- **Under investigation:** Meteocat / AEMET Station Observations; Barcelona Urban Morphology / Open Space Context Layer
- **Coverage gaps:** The comfort benchmark itself is not a dataset; it is handled as an evaluation standard in the brief and system sketch. The open question is whether the city morphology layer is detailed enough for consistent shadow and canyon calculations.
