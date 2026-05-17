# Dataset Datasheet — Barcelona MTM Building Heights / Alçades

> One datasheet per adopted dataset. Save as `docs/datasheets/barcelona-mtm-building-heights.md`.
>
> The datasheet is a contract: this is what this data is, this is what it can do, and this is what it cannot do.

---

## 0. Quick reference

- **Dataset name:** Barcelona Municipal Topographic Map — Building Heights / Alçades (`MTM Alçades`)
- **Version / vintage:** Portal map ID 118; local exported files show GeoPackage last change `2026-04-09`; QGIS project saved `2022-05-13`
- **Source URL:** https://portaldades.ajuntament.barcelona.cat/en/maps/118
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0), according to Open Data BCN listing on datos.gob.es
- **Spatial coverage:** Barcelona municipality; approximate dataset bounds: longitude `2.0556–2.2276`, latitude `41.3161–41.4685`
- **Temporal coverage:** Not a time-series dataset. It represents the municipal topographic/building-height situation at the map/data vintage; exact survey date should be verified from the portal metadata.
- **Native resolution (spatial / temporal):** Building or building-volume polygon level; no temporal resolution.
- **Format:** GeoPackage (`.gpkg`) plus QGIS project (`.qgs`)
- **Size:** Approximately `244 MB` total for the three uploaded GeoPackages:
  - `Base - Alçades.gpkg`: ~189 MB
  - `Sintètic - Alçades.gpkg`: ~45 MB
  - `Situació - Alçades.gpkg`: ~21 MB
- **Coordinate reference system:** EPSG:25831 — ETRS89 / UTM zone 31N
- **Datasheet last updated:** 2026-05-17 by Morris Chang

---

## 1. Motivation

*Why does this dataset exist? Who created it? What was it built for?*

- **Why was the dataset created?**

  The dataset was created to describe building-height and topographic construction information in Barcelona as part of the city’s municipal mapping / topographic data infrastructure.

- **Who created the dataset?**

  Ajuntament de Barcelona / Barcelona City Council, through its municipal data and cartographic services.

- **Who funded the creation of the dataset?**

  Public municipal administration. Exact department-level funding should be verified from the official metadata page if required.

- **For what tasks was the dataset originally intended?**

  Urban cartography, city mapping, planning reference, public geospatial information, and municipal analysis. It was not originally created as an AI training dataset.

---

## 2. Composition

*What does the dataset contain? At what unit? What's missing?*

- **What does an instance represent?**

  Each instance represents a polygon or multipolygon feature related to a building, built volume, simplified building footprint, or height-related topographic element.

- **How many instances are there in total?**

  Based on the uploaded GeoPackages:

  - `Base - Alçades`: `503,596` polygon features
  - `Sintètic - Alçades`: `76,708` polygon features
  - `Situació - Alçades`: `17,373` polygon features

- **What features / fields does each instance have?**

### `Base - Alçades`

| Field | Type | Description | Required? |
|---|---|---|---|
| `FID` | Integer | Unique feature ID | Yes |
| `geometria` | MultiPolygon | Geometry of the feature | Yes |
| `NIVELL` | Text | Topographic/category level code | Yes |
| `AREA` | Real | Polygon area | Yes |
| `PERIMETRE` | Real | Polygon perimeter | Yes |
| `DISTRICTE` | Text | Barcelona district code | Yes |
| `BARRI` | Text | Barcelona neighbourhood code | Yes |
| `Z_MIN_VOL` | Real | Minimum volume/elevation value | Yes |
| `Z_MAX_VOL` | Real | Maximum volume/elevation value | Yes |

### `Sintètic - Alçades`

| Field | Type | Description | Required? |
|---|---|---|---|
| `FID` | Integer | Unique feature ID | Yes |
| `geometria` | MultiPolygon | Geometry of the feature | Yes |
| `NIVELL_BSC` | Text | Simplified/basic level code | Yes |
| `IDSUBTCLAS` | Text | Subclass identifier | Yes |
| `AREA` | Real | Polygon area | Yes |
| `PERIMETRE` | Real | Polygon perimeter | Yes |
| `DISTRICTE` | Text | Barcelona district code | Yes |
| `BARRI` | Text | Barcelona neighbourhood code | Yes |
| `Z_MAX_VOL` | Real | Maximum volume/elevation value | Yes |
| `Z_MIN_VOL` | Real | Minimum volume/elevation value | Yes |

### `Situació - Alçades`

| Field | Type | Description | Required? |
|---|---|---|---|
| `FID` | Integer | Unique feature ID | Yes |
| `geometria` | MultiPolygon | Geometry of the simplified building feature | Yes |
| `ID_INSPIRE` | Text | INSPIRE-related identifier | Yes |
| `NIVELL` | Text | Topographic/category level code | Yes |
| `NIVELL_DESCRIPCIO` | Text | Catalan description of level/category | Yes |
| `NIVELL_DESCRIPCIO_ES` | Text | Spanish description; empty in uploaded file | No |
| `NIVELL_DESCRIPCIO_EN` | Text | English description; empty in uploaded file | No |
| `LLEGENDA` | Text | Legend label | Yes |
| `DISTRICTE` | Text | Barcelona district code | Yes |
| `BARRI` | Text | Barcelona neighbourhood code | Yes |
| `Z_MAX_VOL` | Real | Maximum volume/elevation value | Yes |
| `Z_MIN_VOL` | Real | Minimum volume/elevation value | Yes |
| `AREA` | Float | Polygon area | Yes |
| `PERIMETRE` | Float | Polygon perimeter | Yes |

- **Are there labels or targets associated with each instance?**

  There are no machine-learning labels. However, `NIVELL`, `NIVELL_BSC`, `NIVELL_DESCRIPCIO`, `LLEGENDA`, `DISTRICTE`, `BARRI`, `Z_MIN_VOL`, and `Z_MAX_VOL` can be used as structured attributes for spatial analysis.

- **Is any information missing from instances?**

  In the uploaded files, most core fields have no null values. In `Situació - Alçades`, `NIVELL_DESCRIPCIO_ES` and `NIVELL_DESCRIPCIO_EN` are fully empty, so the Catalan description should be treated as the main category description.

- **Are there relationships between individual instances?**

  Yes. Features are spatially related through adjacency, containment, overlap, district/neighbourhood grouping, and proximity to a user-selected building or site. The `Base`, `Sintètic`, and `Situació` layers appear to represent different levels of generalisation/detail.

- **Are there recommended data splits?**

  No official train/validation/test split is provided. For this project, this dataset should mainly be used for spatial context querying, not supervised model training. If ML is later used, split by district or neighbourhood rather than random polygons to reduce spatial leakage.

---

## 3. Collection process

*How was the data acquired? By whom? When? Is the sample representative?*

- **How was the data acquired?**

  The dataset appears to be a municipal cartographic/topographic dataset derived from official city mapping and geospatial surveying/processing workflows.

- **What instruments / sensors / software were used?**

  Not specified in the uploaded files. Likely municipal GIS/topographic production tools. The provided project file is a QGIS project using EPSG:25831.

- **Who was involved in the data collection process?**

  Barcelona municipal mapping/data services. Specific surveyors or contractors are not identified in the uploaded files.

- **Over what time period was the data collected?**

  Not clearly specified. The QGIS project was saved in 2022 and the uploaded GeoPackages show 2026 internal last-change timestamps, but this does not necessarily mean all geometry was surveyed in 2026.

- **What was the sampling strategy?**

  Exhaustive municipal spatial coverage rather than statistical sampling. The aim is to cover the city’s mapped building/topographic features.

- **Is the sample representative?**

  It is representative for Barcelona municipal building-height/topographic context, but not representative of other cities or building typologies outside Barcelona.

- **Were any ethical review processes conducted?**

  Not relevant in the same way as human-subject datasets. However, downstream use should avoid making resident-level or health-risk claims from building height alone.

---

## 4. Preprocessing & cleaning

*What was done to the data before you got it? What did you do?*

- **What preprocessing was done by the dataset creators?**

  The dataset creators likely converted municipal cartographic data into map-ready GeoPackage layers with category codes, district/neighbourhood attributes, height/elevation values, and QGIS styling. Exact creator-side preprocessing is not documented in the uploaded files.

- **Is the raw data also available?**

  The portal provides downloadable map/GIS resources. Whether more raw survey data exists separately is unknown.

- **What preprocessing did WE do before adopting the dataset?**

  Initial profiling only:

  - inspected GeoPackage metadata and layer names
  - checked CRS: EPSG:25831
  - counted features per layer
  - listed fields and data types
  - checked null counts for non-geometry fields
  - calculated approximate geographic bounds
  - identified `Z_MIN_VOL` and `Z_MAX_VOL` as key height/elevation fields

- **Where is the preprocessing software / code available?**

  Proposed location in the project repo:

  - `notebooks/01-data-profiling.ipynb`
  - `scripts/profile_building_heights.py`
  - `data/processed/barcelona_building_height_context.geojson` or `.parquet`

---

## 5. Uses

*What's this dataset good for? What's it NOT good for?*

- **What tasks has the dataset been used for?**

  Public mapping, urban reference, GIS visualization, and municipal spatial analysis.

- **Is there a repository linking to papers / systems that use this dataset?**

  Not identified yet.

- **What other tasks could this dataset be used for?**

  In our Passive Design Advisor, it can be used for:

  - surrounding building height extraction
  - obstruction and shading-context estimation
  - urban canyon ratio estimation when combined with street-width data
  - wind-sheltering / ventilation-context proxy
  - roof exposure and nearby massing analysis
  - local morphology indicators within 50 m / 100 m buffers
  - supporting the rule-based passive strategy scorecard

- **What tasks should this dataset NOT be used for?**

  1. It should not be used alone to calculate full indoor thermal comfort, because it does not include indoor temperature, occupancy, material properties, HVAC operation, window behaviour, or envelope performance.
  2. It should not be used alone to generate final retrofit design decisions, because building height and footprints only describe urban geometry, not structural condition, construction details, cost, heritage constraints, or resident needs.
  3. It should not be used as a direct training label for passive design quality unless validated with simulation or expert-labelled cases.
  4. It should not be used to make health or vulnerability claims about residents without combining it with appropriate demographic, climate, and heat-risk datasets.

- **Are there any considerations about discrimination, bias, or harm?**

  The dataset itself is physical/geospatial, but harm can occur if the system overinterprets morphology as resident-level vulnerability. Dense or high-rise areas should not automatically be framed as “bad” or “unsafe”; they should be treated as spatial conditions that require further climate, social, and design evidence.

---

## 6. Distribution & licensing

- **Under what license is the dataset distributed?**

  Open Data BCN is listed with Creative Commons Attribution 4.0 International (CC BY 4.0). Confirm the exact license on the dataset page before final submission.

- **Are there restrictions on use, redistribution, attribution, or modification?**

  Reuse and adaptation are generally allowed under CC BY 4.0, with attribution required. Any modified version should indicate that changes were made.

- **What's the required attribution string?**

  Suggested attribution:

  > Contains information from Barcelona City Council / Ajuntament de Barcelona, Open Data BCN, licensed under Creative Commons Attribution 4.0 International (CC BY 4.0). Source: https://portaldades.ajuntament.barcelona.cat/en/maps/118. Modified for Passive Design Advisor project.

- **Are there fees for access?**

  No fees identified.

- **Are there export controls or regulatory restrictions?**

  No export controls identified.

---

## 7. Maintenance

- **Who supports / hosts / maintains the dataset?**

  Barcelona City Council / Ajuntament de Barcelona through the Portal Barcelona Dades / Open Data BCN infrastructure.

- **How can the maintainer be contacted?**

  Use the Open Data BCN contact channel / portal contact form. The exact dataset maintainer contact should be checked on the live portal page.

- **Is there an erratum?**

  No erratum identified in the uploaded files.

- **Will the dataset be updated?**

  Likely yes as part of municipal data maintenance, but the update cycle for this specific map is not confirmed.

- **How often is the dataset updated?**

  Unknown. Treat as periodically maintained municipal spatial data unless the portal provides a specific update frequency.

- **Are older versions available?**

  Not confirmed.

---

## 8. Limitations relative to OUR project

*How does this dataset's character intersect with our problem brief?*

- **Resolution mismatch with our decision unit?**

  The dataset is detailed enough for urban-context analysis around a selected site, but it is not the user’s actual building model. It supports surrounding-context indicators, while the user-provided geometry still needs to define façade orientation, WWR, room depth, operable windows, roof area, and envelope type.

- **Geographic gaps that matter for us?**

  It only covers Barcelona municipality. It is suitable for a central Barcelona MVP but not transferable to other cities without equivalent local height/footprint datasets.

- **Temporal gaps that matter for us?**

  It is not a temporal dataset. It cannot show future development, seasonal variation, construction changes, or heat-wave dynamics.

- **Biases that could distort our conclusions?**

  Possible biases include outdated geometry, inconsistent generalisation between layers, missing/uncertain height interpretation, and overreliance on outdoor morphology for indoor passive design decisions.

- **What additional sources would compensate for these limits?**

  Needed companion datasets:

  - Barcelona EPW weather file for hourly climate indicators
  - UHI / heat comfort or land surface temperature layer
  - street network and street-width data
  - vegetation / green-cover layer
  - user building geometry file or manual form
  - passive strategy threshold CSV
  - passive design papers/standards for RAG explanation
  - optional simulation or reference cases for validation

- **Verdict for our project:** **Primary / essential urban morphology dataset**

  This dataset should be treated as a primary dataset for **urban morphology and surrounding-height context**, but not as the primary dataset for indoor comfort, final retrofit decisions, or climate risk. In the system, it should feed the **Urban Morphology Processor**, which then produces indicators such as obstruction, surrounding height, canyon ratio proxy, wind sheltering proxy, and roof exposure. The rule-based engine can use these indicators, while the LLM should only explain the results after the rule engine has calculated them.
