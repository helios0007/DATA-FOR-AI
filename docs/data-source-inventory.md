# Data Source Inventory — Passive Design Advisor: Barcelona 2025

> Minimum 5 candidate datasets, each scored against the Dataset Assessment
> Rubric. Adopt only if total ≥ 10/14. Reject low scorers — that's the point
> of the rubric.

---

## How to use this file

1. List at least 5 candidate datasets. Don't stop at the first match — survey
   the landscape across the 6 categories (remote sensing optical, remote
   sensing thermal/radar, climate reanalysis, in-situ sensors, biodiversity,
   built environment).
2. For each, fill out provider, access method, and the rubric scoring table.
3. Write a one-paragraph plain-English description.
4. Issue a verdict: **Adopt / Reject / Investigate further.**
5. Only "Adopt" datasets get a full datasheet (`datasheets/<slug>.md`).

---

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

## 1. Barcelona EPW — TMYx Weather File

- **Provider:** University of California Santa Barbara / White Box Technologies / Ladybug Tools community mirror
- **Access method:** Direct download — https://www.ladybug.tools/epwmap/ → file: `ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw`
- **Category:** climate-reanalysis

### Rubric scoring (0–2 per axis)

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | Derived from NOAA ISD + Meteosat reanalysis; TMYx methodology is peer-reviewed and widely cited in building energy literature |
| Resolution match | 2 | Hourly data for a full TMY year; decision unit is building-season, so hourly >> needed |
| Coverage | 2 | Full annual coverage, all required EPW variables present (dry bulb, RH, wind speed/dir, GHR, DNI, DHI) |
| License | 2 | Freely distributed for research and commercial use; no restrictions beyond attribution |
| Access reliability | 2 | Stable bulk download (single .epw file); also mirrored on climate.onebuilding.org |
| Bias clarity | 1 | TMYx methodology documented; known limitation: airport station (El Prat) may underrepresent urban heat island in central Barcelona by 1–2°C in summer nights |
| Maintenance | 1 | TMYx 2004–2018 base period; updated periodically but not annually |
| **TOTAL** | **12/14** | |

### One-paragraph description

The Barcelona TMYx EPW file provides a Typical Meteorological Year at hourly resolution derived from observed airport station data (ICAO 081810, El Prat de Llobregat) blended with ERA5 reanalysis for solar variables. Each record is one hour of the year containing dry-bulb temperature, relative humidity, wind speed and direction, global horizontal radiation, direct normal radiation, and diffuse horizontal radiation. It is the standard base climate input for passive design analysis, comfort modelling, and building energy simulation tools (EnergyPlus, Ladybug, DesignBuilder). Its primary limitation is that it represents the airport microclimate, which is cooler and windier than the dense urban core of central Barcelona; a UHI correction layer is needed to localise it to specific neighbourhoods.

### Verdict

**Adopt.** Essential baseline; already downloaded. Pair with UHI layer (dataset 4) to correct for urban microclimate bias in dense neighbourhoods.

---

## 2. OpenStreetMap Buildings + Roads via Overpass API

- **Provider:** OpenStreetMap contributors / Overpass API (overpass-api.de / overpass-turbo.eu)
- **Access method:** Overpass QL query returning GeoJSON — https://overpass-api.de/api/interpreter
  Example query: `[out:json]; way["building"](around:200,41.3851,2.1734); out geom;`
  Also bulk extract via Geofabrik: https://download.geofabrik.de/europe/spain/cataluna.html
- **Category:** built-environment

### Rubric scoring (0–2 per axis)

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | OSM is the world's most-cited open geospatial dataset; widely used in peer-reviewed urban morphology research |
| Resolution match | 2 | Building footprint polygons at parcel level (~1–5 m accuracy in Barcelona's Eixample); far finer than our 50–150 m analysis radius |
| Coverage | 1 | Building footprints near-complete for central Barcelona; `building:levels` and `height` tags present for ~60–70% of buildings in Eixample — gaps must be filled with neighbourhood averages (3 m/floor assumption) |
| License | 1 | Open Database License (ODbL) — permissive but requires attribution and share-alike on derived databases |
| Access reliability | 2 | Stable public Overpass API (rate-limited for large queries); Geofabrik bulk PBF download is unconditionally stable |
| Bias clarity | 1 | Tag completeness biases documented by OSM community; building height coverage uneven and depends on local contributor activity |
| Maintenance | 2 | Continuously updated; Geofabrik daily extracts |
| **TOTAL** | **11/14** | |

### One-paragraph description

OpenStreetMap provides building footprint polygons with associated tags including `building:levels` (number of above-ground floors) and `height` (total height in metres) for the Barcelona urban area. Each building is a polygon feature with a centroid and a properties dictionary. For the Eixample grid, footprint coverage is excellent; height attribute coverage is partial but sufficient for a 60–70% direct estimate plus neighbourhood-average gap filling. OSM roads can be queried simultaneously to provide street network geometry for canyon width estimation. The ODbL license requires attribution and any published derivative dataset to be shared under the same terms — this is compatible with the project's open-data commitments. A secondary pull via Geofabrik's Catalonia PBF extract is recommended as a stable offline fallback.

### Verdict

**Adopt.** Primary urban morphology source. Use Overpass API for on-demand spatial queries around a user-selected site; use Geofabrik PBF pre-processed extract for the full city pre-processing step. Fill missing heights with `building:levels × 3 m`.

---

## 3. ICGC Alçades — Building Volume Heights (Base layer)

- **Provider:** Institut Cartogràfic i Geològic de Catalunya (ICGC) via Barcelona Portal de Dades
- **Access method:** Direct download — https://portaldades.ajuntament.barcelona.cat/es/mapas/118 → GeoPackage files (`Base_-_Alçades.gpkg`, `Sintètic_-_Alçades.gpkg`, `Situació_-_Alçades.gpkg`)
- **Category:** built-environment (official topographic survey)

### Rubric scoring (0–2 per axis)

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | Produced by ICGC, the official cartographic institute of Catalonia; authoritative topographic survey data |
| Resolution match | 2 | Polygon-level building volumes (~1–5 m geometric accuracy); finer than any raster alternative and directly usable per building footprint |
| Coverage | 2 | Full coverage of Barcelona by district (`DISTRICTE`) and neighbourhood (`BARRI`); 503,596 polygons in the Base layer with no spatial gaps |
| License | 2 | Open data via Barcelona Portal de Dades; free download, attribution required |
| Access reliability | 2 | Stable bulk GeoPackage download; no registration required |
| Bias clarity | 1 | `Z_MIN_VOL` and `Z_MAX_VOL` are absolute elevations above sea level — building height must be derived as `Z_MAX_VOL − Z_MIN_VOL`; zero-height artefacts present (min_h = 0.0 in some records) requiring filtering |
| Maintenance | 1 | Updated periodically by ICGC; update frequency not explicitly stated on portal |
| **TOTAL** | **12/14** | |

### One-paragraph description

The ICGC Alçades dataset provides building volume polygons for the entire city of Barcelona across three levels of detail: Base (503,596 polygons — full detail), Sintètic (76,708 — generalised), and Situació (17,373 — simplified with English descriptions). Each polygon carries `Z_MIN_VOL` and `Z_MAX_VOL` attributes representing absolute elevation above sea level in metres; building height is computed as their difference. The primary layer for this project is `Base - Alçades`, filtered to `NIVELL = 'CON_01pol_PL'` (main building structures, 458,026 polygons, average height ~17 m) and excluding zero-height artefacts with `height_m > 1.0`. This dataset supersedes both OSM height tags and the Copernicus DHM raster for height estimation, providing polygon-level accuracy directly usable for sky view factor, solar obstruction, and canyon ratio calculations.

### Verdict

**Adopt as primary building height source.** Already downloaded. Filter to `CON_01pol_PL` and compute `height_m = Z_MAX_VOL − Z_MIN_VOL`. Use OSM (dataset 2) for footprint geometry and street network; use this dataset for all height values.

---

## 4. Open Data BCN — Thermal Comfort Zones (confort_termic_od)

- **Provider:** Ajuntament de Barcelona via Open Data BCN
- **Access method:** Direct download — https://opendata-ajuntament.barcelona.cat/data/en/dataset/confort-termic → GeoPackage (`confort_termic_od.gpkg`)
- **Category:** remote-sensing-thermal / in-situ-sensors (composite of solar radiation, albedo, and vegetation cover layers)

### Rubric scoring (0–2 per axis)

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | Produced by Ajuntament de Barcelona as part of the municipal Climate Plan; methodology documented on portal; cited in Barcelona heat impact studies |
| Resolution match | 1 | Zone-based polygon layer (381 polygons, avg ~265,000 m²); coarser than building-level but sufficient for neighbourhood-level thermal comfort adjustment via point-in-polygon lookup |
| Coverage | 2 | Full city of Barcelona; 101 km² covered with no spatial gaps |
| License | 2 | Open Data BCN — free download, attribution required; no registration |
| Access reliability | 2 | Stable GeoPackage bulk download from Open Data BCN portal |
| Bias clarity | 1 | Input data vintages documented (solar radiation 2011, albedo 2014, vegetation 2013); known limitation — does not reflect post-2014 urban changes such as superblocks or recent greening interventions; flagged in tool output |
| Maintenance | 0 | No update since original publication; input layers are 10–12 years old |
| **TOTAL** | **10/14** | |

### One-paragraph description

The Barcelona Thermal Comfort Zones dataset classifies the city into six levels of thermal comfort (`gridcode` 1–6) derived by aggregating three physical parameters: incident solar radiation (2011), surface albedo (2014), and vegetation cover (2013), following the methodology of the Barcelona Climate Plan. The scale runs from `1` (very high comfort — coolest, most shaded, most vegetated zones) to `6` (very low comfort — highest solar exposure, lowest albedo, least vegetation). The dataset contains 381 multipolygon features covering 101 km² in EPSG:25831. In the pipeline it is used as a point-in-polygon lookup: given the user's site coordinates, the tool queries which comfort zone the site falls in and uses the `gridcode` to adjust the base EPW overheating risk — a site in zone 5 or 6 pushes all cooling strategy scores upward. The data vintage (2011–2014) is a known limitation and is flagged in the tool's output as a caveat.

### Verdict

**Adopt.** Already downloaded. Use as a spatial lookup table via `gdf[gdf.contains(user_point)]['gridcode']`. Note scale direction in the rule engine: `gridcode 1` = best comfort, `gridcode 6` = worst. Document the 2011–2014 data vintage prominently in the tool UI.

---

## 5. Copernicus Street Tree Layer (STL) 2018 — Barcelona

- **Provider:** European Environment Agency / Copernicus Land Monitoring Service
- **Access method:** Registered free download — https://land.copernicus.eu/local/urban-atlas → "Street Tree Layer 2018" → Barcelona FUA tile
- **Category:** remote-sensing-optical (derived from VHR satellite imagery + classification)

### Rubric scoring (0–2 per axis)

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | EU Copernicus programme; peer-reviewed methodology; used in multiple urban ecology and climate adaptation studies |
| Resolution match | 2 | Polygon features at individual tree-canopy resolution (~2–5 m MMU) — finer than our site-level green cover ratio need |
| Coverage | 2 | Full coverage of Barcelona FUA; no gaps |
| License | 2 | Full, open and free access under Copernicus data policy |
| Access reliability | 1 | Requires free registration; one-time bulk download; no live API |
| Bias clarity | 1 | Known to miss small isolated trees below minimum mapping unit; classification accuracy ~85–90% documented in EEA technical reports |
| Maintenance | 1 | Reference year 2018; next update not confirmed |
| **TOTAL** | **11/14** | |

### One-paragraph description

The Copernicus Street Tree Layer 2018 is a polygon dataset delineating the crown extent of individual street trees and small tree clusters within the Barcelona Functional Urban Area, derived from very high resolution satellite imagery. Each polygon represents a tree or group of trees with a minimum mapping unit of approximately 4 m². For the passive design tool, this layer is used to compute the green cover ratio within a buffer around the user's site, which supports two checks: (1) whether a green roof is ecologically justified as an extension of the local green network, and (2) whether tree shading is already reducing solar exposure on specific façades. OSM natural/landuse tags can be used as a fast alternative for a first pass, but the STL provides a more accurate and reproducible vegetation extent. It does not contain NDVI values or tree height.

### Verdict

**Adopt.** Download alongside the DHM. Pre-process to compute green_cover_ratio within 50 m and 100 m buffers for any site in Barcelona; store as a lookup raster or spatial index for fast query.

---

## 6. Passive Design Academic Papers — RAG Knowledge Base

- **Provider:** Multiple — MDPI (open access), ResearchGate, academia.edu, Springer, Building and Environment journal
- **Access method:** Individual PDF downloads from DOIs listed below; all are open access or freely accessible
- **Category:** *(special category: literature / standards — used for RAG, not spatial analysis)*

### Core papers to acquire (all open access or author preprints available)

| Paper | Key relevance | DOI / source |
|---|---|---|
| Givoni (1994) *Passive and Low Energy Cooling of Buildings* | Cross-ventilation and night purge thresholds; widely cited | Book — obtain via library |
| Santamouris & Asimakopoulos (1996) *Passive Cooling of Buildings* | Mediterranean passive strategy reference | Book |
| Szokolay (2004) *Introduction to Architectural Science* | Shading and solar geometry thresholds | Book |
| Lapisa et al. (2018) *Parametric study, Mediterranean passive design, EN 15251* | Shading, WWR, night vent, thermal mass vs EN 15251 comfort | DOI: 10.1051/sbuild/2018004 |
| De Gracia & Cabeza (2015) *Phase change materials and thermal energy storage* | Thermal mass evidence base | Building and Environment |
| Evola et al. (2017) *Natural ventilation Mediterranean apartments* | Cross-ventilation + night purge quantification | Springer Building Simulation |
| Dolado et al. (2021) *Passive cooling Mediterranean social housing* | Solar shading + ventilation for Southern Spain | PMC9081669 |
| Balaras (1996) *Role of thermal mass on the cooling load, night ventilation* | Thermal mass + night purge interaction | Energy and Buildings |
| Comparison of EN 15251 vs ASHRAE 55 (Mediterranean context) | Standard benchmarking for comfort model selection | Academia.edu (open preprint) |

### Rubric scoring (0–2 per axis)

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | Peer-reviewed journals and established textbooks; all cited in building energy and passive design literature |
| Resolution match | 2 | Threshold values (°C, m/s, WWR ratios, room depth limits) are directly usable as rule-engine parameters |
| Coverage | 1 | Good coverage of shading, ventilation, thermal mass, night purge; green roof evidence base thinner — supplement with CIBSE TM44 or IEA Annex 62 |
| License | 1 | Mix of open access (MDPI, PMC) and restricted (Elsevier, Springer) — for RAG, text extraction for internal research use is defensible; check institutional access |
| Access reliability | 1 | Manual PDF download per paper; no API |
| Bias clarity | 1 | Most papers document their simulation assumptions and climate inputs; threshold values vary across studies |
| Maintenance | 2 | Classic references stable; newer papers (2015–2021) represent current practice |
| **TOTAL** | **10/14** | |

### One-paragraph description

This is not a single dataset but a curated bundle of peer-reviewed papers and standard references that form the knowledge base for the RAG (retrieval-augmented generation) component of the tool. Each paper provides quantitative thresholds or qualitative evidence for one or more passive strategy checks: for example, the Lapisa (2018) Malta case study uses EN 15251 as its comfort benchmark for a Mediterranean climate and parametrically tests shading, WWR, night ventilation, and thermal mass — making it directly reusable for threshold justification. Papers will be cleaned (OCR if needed), chunked by section, tagged by strategy topic (shading / ventilation / thermal mass / night purge / green roof / comfort standard), and embedded into a vector store (FAISS or ChromaDB). Claude then retrieves the most relevant chunks to support and cite each strategy recommendation.

### Verdict

**Adopt.** Prioritise open-access papers (MDPI, PMC) first. Obtain the Lapisa 2018 and Evola 2017 papers immediately — they are the closest match to your climate zone and comfort standard. Add CIBSE TM44 for green roof evidence.

---

## 7. EN 15251 / ASHRAE 55 — Adaptive Comfort Thresholds (Encoded Lookup Table)

- **Provider:** CEN (European Committee for Standardisation) / ASHRAE
- **Access method:** The standards themselves require institutional purchase; however, the key adaptive comfort equations and tables are extensively reproduced and explained in open-access literature (Nicol & Humphreys 2010, de Dear & Brager 1998). The operative equations and threshold tables can be transcribed manually from the standards into a JSON/CSV lookup.
- **Category:** *(special category: standards — encoded as rule-engine parameters)*

### Rubric scoring (0–2 per axis)

| Axis | Score | Justification |
|---|---|---|
| Provenance | 2 | International standards bodies; equations behind both standards are published in open peer-reviewed papers |
| Resolution match | 2 | Thresholds operate on running mean outdoor temperature — directly computable from EPW hourly data |
| Coverage | 2 | Both standards cover naturally ventilated buildings in warm climates; Barcelona falls squarely within their applicability range |
| License | 0 | Standards are copyrighted and must be purchased; however, the mathematical content (equations, threshold tables) can be re-implemented from open literature without reproducing the standards text |
| Access reliability | 2 | Once encoded as a lookup table, fully self-contained in the repo — no external dependency |
| Bias clarity | 2 | Extensive peer-reviewed debate on applicability of both models in Mediterranean climate; differences documented (EN 15251 allows ~1–2°C higher upper limit than ASHRAE 55 for warm climates) |
| Maintenance | 1 | EN 15251 is superseded by EN 16798-1 (2019); ASHRAE 55 updated to 2023 edition — use the latest versions |
| **TOTAL** | **11/14** | |

### One-paragraph description

The adaptive comfort models from EN 16798-1:2019 (formerly EN 15251) and ASHRAE 55:2023 define acceptable indoor operative temperatures as a function of the outdoor running mean temperature for naturally ventilated buildings. For Barcelona's summer (running mean outdoor temp ~24–28°C), EN 16798-1 Category II sets an upper comfort limit of approximately 27–28°C operative temperature, while ASHRAE 55's 80% acceptability band sets a similar range. These thresholds are the benchmark against which the rule engine judges whether passive strategies can maintain comfort without mechanical cooling. The recommendation is to implement EN 16798-1 as the primary standard (it is the European building code reference and more permissive in warm climates, which is appropriate for Mediterranean passive design) and include ASHRAE 55 as a secondary check. Both will be encoded as a Python function and a JSON lookup table in the repo, using the open-literature formulations of the underlying equations.

### Verdict

**Adopt.** Encode as a 3-column CSV: `[running_mean_outdoor_temp, EN16798_upper_cat2, ASHRAE55_upper_80pct]`. This is a 1–2 hour task. Use EN 16798-1 as the default, note where the two standards diverge.

---

## Summary

- **Adopted:** Barcelona EPW (1), OSM buildings + roads (2), ICGC Alçades building heights (3), Open Data BCN thermal comfort zones (4), Copernicus Street Tree Layer (5), passive design papers bundle (6), EN 16798-1 / ASHRAE 55 encoded thresholds (7)
- **Rejected:** none at this stage
- **Under investigation:** none at this stage

### Coverage gaps flagged

| Gap | Impact | Mitigation |
|---|---|---|
| OSM footprints used for geometry but heights now fully covered by ICGC Alçades | Low — height gap closed; footprint geometry remains OSM-dependent | Cross-check ICGC polygon boundaries against OSM footprints for a sample block |
| EPW represents airport microclimate, not urban core | Medium — may underestimate nighttime temps by 1–2°C in dense areas | Partially corrected by thermal comfort zone lookup (dataset 4); flag as known uncertainty in tool output |
| Thermal comfort layer input data is 2011–2014 vintage | Medium — does not reflect post-2014 greening or superblock interventions | Flag prominently in tool UI; treat as indicative zone, not precise measurement |
| Street canyon width not explicitly in any dataset | Low — can be derived from OSM road geometry + building footprint distance | Compute from OSM road linestring buffer intersected with ICGC building footprints |
| Green roof evidence base thin | Low — limited to Copernicus STL + secondary literature | Add CIBSE TM44 green roof section to RAG bundle |
| No real-time or recent (post-2020) wind data | Low — EPW wind stats adequate for screening-level tool | Flag in tool UI: wind assessment is indicative only |
| Standards text (EN 16798-1) not freely available | Low — equations reproducible from open literature | Encode from Nicol & Humphreys 2010 + free-access papers; do not reproduce standards text |

### Acquisition priority order (do this week)

1. ✅ EPW file — already downloaded
2. ✅ ICGC Alçades — already downloaded (Base, Sintètic, Situació gpkg files)
3. ✅ Open Data BCN thermal comfort — already downloaded (`confort_termic_od.gpkg`)
4. OSM Barcelona buildings PBF — download from Geofabrik Catalonia extract (~150 MB)
5. Copernicus Street Tree Layer 2018 — register on Copernicus portal and download Barcelona FUA tile
6. Paper PDFs — download the 5 highest-priority open-access papers listed in dataset 6
7. Encode EN 16798-1 thresholds — 2 hours transcription from Nicol & Humphreys 2010
