# Passive Design Advisor — Barcelona 2025
## Complete Build Specification for Claude Code

> This document is the authoritative specification for building the Passive Design
> Advisor tool. Follow every section in order. Do not skip sections. All formulas,
> weights, and thresholds have mandatory literature citations — implement them exactly
> as specified. Do not substitute values from general knowledge.

Before building build_rag.py, first build scripts/chunk_papers.py. This script should: read every PDF in data/rag_documents/papers/ using pypdf, split each paper into chunks of ~400 words with 50-word overlap, tag each chunk with source, strategy (inferred from filename — e.g. a file named balaras_1996.pdf gets strategy: thermal_mass), and page number, then write the results as JSON arrays to data/rag_documents/chunks/<filename>.json. Add pypdf>=3.0.0 to requirements.txt.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Structure](#2-repository-structure)
3. [Dependencies](#3-dependencies)
4. [Pipeline Overview](#4-pipeline-overview)
5. [Stage 1 — IFC Parsing and Feature Extraction](#5-stage-1--ifc-parsing-and-feature-extraction)
6. [Stage 2 — Context Enrichment from Geospatial Data](#6-stage-2--context-enrichment-from-geospatial-data)
7. [Stage 3 — Simplified Thermal Diagnosis](#7-stage-3--simplified-thermal-diagnosis)
8. [Stage 4 — Strategy Scoring Model (MAUT)](#8-stage-4--strategy-scoring-model-maut)
9. [Stage 5 — LLM Recommendation Generation with GraphRAG](#9-stage-5--llm-recommendation-generation-with-graphrag)
10. [User Inputs and Outputs](#10-user-inputs-and-outputs)
11. [Data Dependencies and File Paths](#11-data-dependencies-and-file-paths)
12. [GraphRAG Knowledge Base Specification](#12-graphrag-knowledge-base-specification)
13. [LLM Prompt Templates](#13-llm-prompt-templates)
14. [Output Format Specification](#14-output-format-specification)
15. [Validation and Testing](#15-validation-and-testing)

---

## 1. Project Overview

### Purpose

A design-phase tool for architects working on new buildings in central Barcelona.
Given a 3D building model (IFC format) and a site location, the tool:

1. Extracts building geometry and enriches it with urban and climate context
2. Diagnoses the building's current estimated overheating risk
3. Evaluates five passive design strategies using a multi-criteria weighted scoring model
4. Ranks strategies by their estimated impact on thermal comfort
5. Outputs specific geometric recommendations referencing the user's own IFC model elements
6. Explains the reasoning with citations to certified standards and literature via GraphRAG

### What the tool is NOT

- Not an energy compliance or certification tool
- Not a retrofit advisor (design phase only, no existing buildings)
- Not a full thermal simulation (EnergyPlus, DesignBuilder, etc.)
- Not a real-time monitoring dashboard
- Not applicable outside central Barcelona neighbourhoods

### Scoring methodology

The tool uses **Multi-Attribute Utility Theory (MAUT)** — a formally published
decision framework used extensively in building performance research. Each passive
strategy receives an impact score (0–100) representing the estimated reduction in
**Overheating Degree Hours (ODH)** if that strategy is implemented.

ODH is the metric defined in EN 16798-1:2019 (formerly EN 15251) for assessing
overheating risk in naturally ventilated buildings:

```
ODH = Σ max(0, T_operative_h - T_comfort_limit_h)   for all hours h in year
```

Each factor in the MAUT scoring is a proxy for ODH reduction, with weights derived
from published sensitivity analyses in Mediterranean climate building performance
literature. This distinguishes the model from a heuristic: thresholds and weights
are data-derived from peer-reviewed sources, not manually assumed.

---

## 2. Repository Structure

Create exactly this structure:

```
passive-design-advisor/
│
├── data/
│   ├── ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw
│   ├── Base_-_Alçades.gpkg
│   ├── Sintètic_-_Alçades.gpkg
│   ├── Situació_-_Alçades.gpkg
│   ├── confort_termic_od.gpkg
│   └── rag_documents/
│       ├── chunks/              # populated by scripts/build_rag.py
│       └── papers/              # PDF files placed here manually
│
├── scripts/
│   ├── parse_epw.py             # already built — outputs outputs/epw_summary.json
│   ├── build_rag.py             # builds ChromaDB vector store from rag_documents
│   └── build_graph.py           # builds NetworkX strategy graph
│
├── src/
│   ├── __init__.py
│   ├── ifc_parser.py            # Stage 1
│   ├── context_enricher.py      # Stage 2
│   ├── thermal_diagnosis.py     # Stage 3
│   ├── strategy_scorer.py       # Stage 4
│   ├── recommender.py           # Stage 5 — LLM + GraphRAG
│   └── utils.py                 # shared helpers
│
├── outputs/
│   ├── epw_summary.json         # produced by parse_epw.py
│   └── reports/                 # tool outputs written here
│
├── graph/
│   ├── strategy_graph.json      # produced by build_graph.py
│   └── chroma_db/               # produced by build_rag.py
│
├── main.py                      # CLI entry point
├── requirements.txt
└── README.md
```

---

## 3. Dependencies

### requirements.txt

```
ifcopenshell>=0.7.0
geopandas>=0.14.0
pvlib>=0.10.0
pandas>=2.0.0
numpy>=1.24.0
shapely>=2.0.0
pyproj>=3.5.0
chromadb>=0.4.0
sentence-transformers>=2.2.0
networkx>=3.1
anthropic>=0.25.0
python-dotenv>=1.0.0
rich>=13.0.0
```

### Environment variables (.env file — never commit this)

```
ANTHROPIC_API_KEY=your_key_here
```

---

## 4. Pipeline Overview

```
INPUT: building.ifc + site_lat + site_lon + building_use
          │
          ▼
┌─────────────────────────────────────────────┐
│  STAGE 1: IFC Parser (src/ifc_parser.py)    │
│  Extract geometry features per element      │
│  Output: BuildingFeatures dataclass         │
└─────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│  STAGE 2: Context Enricher                  │
│  (src/context_enricher.py)                  │
│  Spatial join: ICGC heights, thermal zones  │
│  EPW climate summary lookup                 │
│  Output: SiteContext dataclass              │
└─────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│  STAGE 3: Thermal Diagnosis                 │
│  (src/thermal_diagnosis.py)                 │
│  Simplified proxy ODH per facade element    │
│  Output: ThermalDiagnosis dataclass         │
└─────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│  STAGE 4: Strategy Scorer (MAUT)            │
│  (src/strategy_scorer.py)                   │
│  5 strategies × (precondition + MAUT score) │
│  Output: List[StrategyScore] ranked         │
└─────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────┐
│  STAGE 5: Recommender                       │
│  (src/recommender.py)                       │
│  GraphRAG retrieval + Anthropic API         │
│  Geometric instructions ref. IFC element IDs│
│  Output: FinalReport                        │
└─────────────────────────────────────────────┘
          │
          ▼
OUTPUT: JSON report + markdown report + console summary
```

---

## 5. Stage 1 — IFC Parsing and Feature Extraction

### File: `src/ifc_parser.py`

### Purpose

Parse the user's IFC file to extract all geometric and construction features
needed for thermal analysis. Every extracted feature must retain the originating
IFC element's GlobalId so recommendations can reference it precisely.

### Data Classes

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class FacadeFeature:
    """One exterior wall facade with its windows."""
    element_id: str          # IFC GlobalId of the IfcWall
    orientation_deg: float   # 0=N, 90=E, 180=S, 270=W (compass bearing of outward normal)
    orientation_label: str   # "N", "NE", "E", "SE", "S", "SW", "W", "NW"
    gross_area_m2: float     # total wall area including windows
    window_area_m2: float    # sum of all window areas on this facade
    wwr: float               # window-to-wall ratio (0.0–1.0)
    window_element_ids: list[str]   # IFC GlobalIds of IfcWindow elements
    u_value: Optional[float]        # W/m²K from IFC material properties; None if unavailable
    construction_mass: str          # "lightweight" / "medium" / "heavy" — see mapping below
    shading_factor: float           # existing shading coefficient (0=fully shaded, 1=unshaded)
    is_exterior: bool               # True if wall faces exterior

@dataclass
class RoofFeature:
    """The building roof."""
    element_id: str
    area_m2: float
    is_exposed: bool         # True if no floor above
    inclination_deg: float   # 0=flat, >0=pitched
    u_value: Optional[float]
    construction_mass: str

@dataclass
class BuildingFeatures:
    """All extracted features from the IFC model."""
    ifc_file_path: str
    site_latitude: float
    site_longitude: float
    building_use: str          # "residential" / "office" / "mixed"
    total_floor_area_m2: float
    floor_to_ceiling_height_m: float
    building_depth_m: float    # longest horizontal dimension for cross-ventilation check
    building_width_m: float    # shortest horizontal dimension
    number_of_floors: int
    facades: list[FacadeFeature]
    roof: RoofFeature
    has_opposing_openings: bool   # True if windows exist on facades >= 135° apart
    operable_window_area_m2: float  # from IfcWindowType.OperationType if available
```

### Construction Mass Mapping

Map IFC material names and layer thicknesses to mass categories.
Check `IfcMaterialLayer.Material.Name` and `IfcMaterialLayer.LayerThickness`.

```python
MASS_MAPPING = {
    # keywords in material name → mass category
    "concrete": "heavy",
    "brick": "heavy",
    "masonry": "heavy",
    "stone": "heavy",
    "rammed earth": "heavy",
    "timber frame": "lightweight",
    "steel frame": "lightweight",
    "curtain wall": "lightweight",
    "sandwich panel": "lightweight",
    "insulated panel": "lightweight",
    "CLT": "medium",
    "cross laminated": "medium",
    "block": "medium",
}
# Default if material name not matched: "medium"

MASS_SCORE = {
    "lightweight": 0.0,
    "medium": 0.5,
    "heavy": 1.0
}
```

### Orientation Mapping

```python
def degrees_to_label(deg: float) -> str:
    """Convert compass bearing (0=N) to 8-point label."""
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((deg + 22.5) / 45) % 8
    return labels[idx]
```

### Shading Factor Detection

Check for `IfcShading`, `IfcShadingDevice`, or `IfcAnnotation` elements associated
with a wall. If present, set `shading_factor = 0.3` (partial shading assumed).
If absent, set `shading_factor = 1.0` (unshaded).
If `IfcShadingDevice` has `ShadingDeviceType = "OVERHANG"`, set `shading_factor = 0.5`.

### Opposing Openings Detection

Two facades have opposing openings if their orientations differ by 135°–225°.
Set `has_opposing_openings = True` if at least one such pair exists with
window area > 0 on both facades.

### Building Depth Calculation

```python
# Get bounding box from IfcBuilding or IfcBuildingStorey geometry
# building_depth_m = max horizontal dimension (for cross-ventilation worst case)
# building_width_m = min horizontal dimension
```

### Operable Window Area

Check `IfcWindowType.OperationType`. Count area as operable if:
- `SINGLE_SWING_LEFT`, `SINGLE_SWING_RIGHT`
- `DOUBLE_SWING_LEFT`, `DOUBLE_SWING_RIGHT`
- `TILT_AND_TURN_LEFT`, `TILT_AND_TURN_RIGHT`
- `PIVOT_HORIZONTAL`, `PIVOT_VERTICAL`
- `SLIDING`

If `OperationType` is absent, assume 60% of window area is operable (conservative default).

### Implementation Notes for ifcopenshell

```python
import ifcopenshell
import ifcopenshell.util.element
import ifcopenshell.util.shape
import ifcopenshell.geom
import numpy as np

def get_wall_outward_normal(wall, settings) -> np.ndarray:
    """Returns the outward-facing normal vector of a wall as [x, y, z]."""
    shape = ifcopenshell.geom.create_shape(settings, wall)
    verts = np.array(shape.geometry.verts).reshape(-1, 3)
    faces = np.array(shape.geometry.faces).reshape(-1, 3)
    # Compute face normals and average → outward normal
    # Then convert local to global using wall placement matrix
    ...

def normal_to_compass_bearing(normal: np.ndarray) -> float:
    """Convert XY normal vector to compass bearing (0=N, 90=E, 180=S, 270=W)."""
    angle = np.degrees(np.arctan2(normal[0], normal[1]))
    return (angle + 360) % 360

def get_windows_on_wall(wall, model) -> list:
    """Returns all IfcWindow elements hosted by this wall."""
    return [
        rel.RelatedBuildingElement
        for rel in model.by_type("IfcRelFillsElement")
        if rel.RelatingOpeningElement in
           [v.RelatedOpeningElement for v in wall.HasOpenings]
    ]
```

---

## 6. Stage 2 — Context Enrichment from Geospatial Data

### File: `src/context_enricher.py`

### Purpose

Attach urban morphology and climate context to the building features extracted
in Stage 1. All spatial operations use EPSG:25831 (UTM zone 31N — the native CRS
of the Barcelona datasets).

### Data Classes

```python
@dataclass
class SiteContext:
    # Urban morphology
    svf_mean: float              # Sky View Factor (0–1), averaged around site
    canyon_hw_ratio: float       # mean H/W ratio of adjacent streets
    canyon_wind_correction: float # multiplier applied to EPW wind speed (0.3–0.9)
    surrounding_heights_m: list[float]  # heights of buildings within 150m radius
    solar_obstruction_angles: dict      # {orientation: max obstruction angle in degrees}
                                        # e.g. {"S": 15.0, "W": 22.0, ...}
    green_cover_ratio_50m: float  # fraction of area within 50m that is vegetation

    # Thermal comfort zone
    thermal_comfort_gridcode: int   # 1 (best) to 6 (worst) from confort_termic_od
    thermal_comfort_label: str      # "Very High" / "High" / "Medium" / "Medium-Low" / "Low" / "Very Low"

    # Climate (from epw_summary.json)
    july_diurnal_swing_C: float
    summer_mean_temp_C: float
    summer_peak_temp_C: float
    summer_CDH_above_26C: float
    dominant_wind_direction: str
    summer_mean_wind_m_s: float
    night_purge_hours_below_22C: int
    july_EN16798_upper_C: float
    july_ASHRAE55_upper_C: float
    summer_mean_GHI_Wh_m2: float
    summer_peak_GHI_Wh_m2: float
```

### Sky View Factor Calculation

SVF is computed from the surrounding building heights extracted from
`Base_-_Alçades.gpkg` (layer: `Base - Alçades`).

```python
import geopandas as gpd
from shapely.geometry import Point
import numpy as np

BUILDING_LAYER = "Base - Alçades"
SEARCH_RADIUS_M = 150
PRIMARY_NIVELL = "CON_01pol_PL"

def load_buildings(gpkg_path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(gpkg_path, layer=BUILDING_LAYER)
    gdf = gdf[gdf["NIVELL"] == PRIMARY_NIVELL].copy()
    gdf["height_m"] = gdf["Z_MAX_VOL"] - gdf["Z_MIN_VOL"]
    gdf = gdf[gdf["height_m"] > 1.0]
    return gdf

def compute_svf(site_point: Point, buildings_gdf: gpd.GeoDataFrame,
                site_height_m: float = 1.5) -> float:
    """
    Simplified SVF calculation using surrounding building obstruction angles.
    Based on: Lindberg et al. 2018, Urban Climate 24:688–701.

    SVF = 1 - (1/2π) × Σ sin²(α_i) × Δθ_i

    where α_i is the obstruction angle in direction θ_i.
    """
    buffer = site_point.buffer(SEARCH_RADIUS_M)
    nearby = buildings_gdf[buildings_gdf.geometry.intersects(buffer)].copy()

    if len(nearby) == 0:
        return 1.0  # no obstructions

    n_sectors = 36  # 10° sectors
    delta_theta = 2 * np.pi / n_sectors
    svf_sum = 0.0

    for i in range(n_sectors):
        angle_rad = i * delta_theta
        # Find max obstruction angle in this sector
        max_alpha = 0.0
        for _, row in nearby.iterrows():
            centroid = row.geometry.centroid
            dist = site_point.distance(centroid)
            if dist < 1.0:
                continue
            bearing = np.arctan2(centroid.x - site_point.x,
                                  centroid.y - site_point.y)
            sector_diff = abs(((bearing - angle_rad + np.pi) % (2*np.pi)) - np.pi)
            if sector_diff < delta_theta / 2:
                h = max(0, row["height_m"] - site_height_m)
                alpha = np.arctan2(h, dist)
                max_alpha = max(max_alpha, alpha)
        svf_sum += np.sin(max_alpha) ** 2 * delta_theta

    svf = 1.0 - svf_sum / (2 * np.pi)
    return float(np.clip(svf, 0.0, 1.0))
```

### Canyon H/W Ratio and Wind Correction

```python
# Canyon H/W ratio: mean building height within 50m / street width
# Street width approximated from OSM (not available in current datasets)
# Fallback: estimate from building footprint spacing

def get_canyon_wind_correction(hw_ratio: float) -> float:
    """
    Wind speed correction factor for street canyon geometry.
    Source: Blocken B. et al. 2007, J. Wind Eng. Ind. Aerodyn. 95(9):941–962
    Table 3 — mean velocity ratio at pedestrian height.

    v_canyon = v_EPW × correction_factor
    """
    if hw_ratio < 0.5:
        return 0.9
    elif hw_ratio < 1.0:
        return 0.7
    elif hw_ratio < 2.0:
        return 0.5
    else:
        return 0.3
```

### Solar Obstruction Angles

```python
def compute_obstruction_angles(
    site_point: Point,
    buildings_gdf: gpd.GeoDataFrame,
    site_height_m: float = 10.0,
    orientations: list[str] = ["N","NE","E","SE","S","SW","W","NW"]
) -> dict[str, float]:
    """
    For each compass orientation, compute the maximum solar obstruction angle
    (elevation angle above horizon blocked by surrounding buildings).
    Used for shading and solar irradiance calculations.

    Source: Szokolay S.V. 2004, Introduction to Architectural Science,
    Architectural Press, §2.3.
    """
    orientation_deg = {"N":0,"NE":45,"E":90,"SE":135,"S":180,"SW":225,"W":270,"NW":315}
    result = {}
    for label, bearing in orientation_deg.items():
        bearing_rad = np.radians(bearing)
        sector_width = np.radians(45)
        max_angle = 0.0
        for _, row in buildings_gdf.iterrows():
            centroid = row.geometry.centroid
            dist = site_point.distance(centroid)
            if dist < 1.0:
                continue
            b = np.arctan2(centroid.x - site_point.x, centroid.y - site_point.y)
            diff = abs(((b - bearing_rad + np.pi) % (2*np.pi)) - np.pi)
            if diff < sector_width / 2:
                h = max(0, row["height_m"] - site_height_m)
                alpha = np.degrees(np.arctan2(h, dist))
                max_angle = max(max_angle, alpha)
        result[label] = round(max_angle, 1)
    return result
```

### Thermal Comfort Zone Lookup

```python
COMFORT_LABELS = {1:"Very High", 2:"High", 3:"Medium", 4:"Medium-Low", 5:"Low", 6:"Very Low"}

def get_thermal_comfort_zone(site_point: Point, gpkg_path: str) -> tuple[int, str]:
    """
    Point-in-polygon lookup against confort_termic_od.gpkg.
    Returns (gridcode, label).
    gridcode 1 = Very High comfort (coolest); gridcode 6 = Very Low comfort (hottest).
    Source: Ajuntament de Barcelona, Open Data BCN — confort-termic dataset.
    NOTE: Scale is inverted — gridcode 6 means WORST thermal comfort.
    """
    gdf = gpd.read_file(gpkg_path)
    gdf = gdf.to_crs("EPSG:25831")
    matches = gdf[gdf.geometry.contains(site_point)]
    if len(matches) == 0:
        # fallback: nearest polygon
        gdf["dist"] = gdf.geometry.distance(site_point)
        matches = gdf.nsmallest(1, "dist")
    gridcode = int(matches.iloc[0]["gridcode"])
    return gridcode, COMFORT_LABELS[gridcode]
```

---

## 7. Stage 3 — Simplified Thermal Diagnosis

### File: `src/thermal_diagnosis.py`

### Purpose

Compute a proxy estimate of current Overheating Degree Hours (ODH) and identify
which building elements are the primary contributors to overheating risk.
This is NOT a full thermal simulation. It is a physics-based proxy model that
estimates the relative thermal stress per facade, justified by:

> Thermal comfort in naturally ventilated buildings is primarily governed by
> solar heat gain through glazing, ventilation cooling rate, and thermal mass
> buffering. EN 16798-1:2019 Annex F provides simplified calculation methods
> for these interactions.

### Data Classes

```python
@dataclass
class FacadeThermalStress:
    element_id: str
    orientation_label: str
    solar_heat_gain_index: float    # normalised 0–1, higher = more solar gain
    ventilation_cooling_index: float # normalised 0–1, higher = more cooling available
    net_thermal_stress: float        # solar_gain - ventilation_cooling, proxy for ODH contribution
    is_critical: bool                # True if net_thermal_stress in top 2 facades

@dataclass
class ThermalDiagnosis:
    estimated_proxy_ODH: float         # sum of net_thermal_stress across all facades × scaling
    critical_facades: list[str]        # element_ids of highest-stress facades
    ventilation_deficit: bool          # True if building cannot self-cool
    night_purge_viable: bool           # True if night cooling hours sufficient
    thermal_mass_deficit: bool         # True if construction is lightweight AND diurnal swing low
    overheating_risk_level: str        # "LOW" / "MEDIUM" / "HIGH" / "CRITICAL"
    diagnosis_text: str                # one-paragraph plain English summary
```

### Solar Heat Gain Index per Facade

```
SHGI_i = GHI_facade_i × WWR_i × SHGC × (1 - shading_factor_i) × orientation_weight_i

where:
  GHI_facade_i     = mean summer GHI on facade orientation i (Wh/m²)
                     Computed from EPW horizontal GHI + pvlib tilt/orientation correction
                     using pvlib.irradiance.get_total_irradiance()
  WWR_i            = window-to-wall ratio of facade i
  SHGC             = 0.6 (default clear glass solar heat gain coefficient)
                     Use IFC material value if available
                     Source: EN 410:2011 Table 2, clear float glass
  shading_factor_i = from IFC (Stage 1); 1.0 if no shading detected
  orientation_weight_i = solar exposure weight by orientation at Barcelona lat 41°N
                         Source: Szokolay 2004, Table 2.3

ORIENTATION_WEIGHTS = {
    "N": 0.10, "NE": 0.30, "E": 0.55,
    "SE": 0.75, "S": 0.85, "SW": 0.95,
    "W": 0.75, "NW": 0.35
}

Normalise SHGI_i to [0,1] across all facades.
```

### pvlib Facade Irradiance Calculation

```python
import pvlib
import json
import pandas as pd

ORIENTATION_TO_AZIMUTH = {
    "N": 0, "NE": 45, "E": 90, "SE": 135,
    "S": 180, "SW": 225, "W": 270, "NW": 315
}

def get_facade_summer_ghi(
    orientation_label: str,
    site_lat: float,
    site_lon: float,
    epw_path: str
) -> float:
    """
    Returns mean summer (JJA) plane-of-array irradiance (Wh/m²)
    for a vertical facade at given orientation.
    Uses pvlib.irradiance.get_total_irradiance with Perez model.
    Source: Perez R. et al. 1990, Solar Energy 44(5):271–289.
    """
    df, meta = pvlib.iotools.read_epw(epw_path)
    df.index = pd.date_range("2001-01-01", periods=8760, freq="h")
    summer = df[df.index.month.isin([6, 7, 8])]

    location = pvlib.location.Location(
        latitude=site_lat, longitude=site_lon, tz="Etc/GMT-1"
    )
    solar_pos = location.get_solarposition(summer.index)

    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=90,
        surface_azimuth=ORIENTATION_TO_AZIMUTH[orientation_label],
        solar_zenith=solar_pos["apparent_zenith"],
        solar_azimuth=solar_pos["azimuth"],
        dni=summer["dni"],
        ghi=summer["ghi"],
        dhi=summer["dhi"],
        model="perez"
    )
    return float(poa["poa_global"].mean())
```

### Ventilation Cooling Index per Facade

```
VCI = min(1.0, (v_canyon × A_inlet_i / A_floor) / threshold)

where:
  v_canyon     = EPW summer mean wind speed × canyon_wind_correction
  A_inlet_i    = operable window area on facade i (m²)
  A_floor      = total floor area of building (m²)
  threshold    = 0.05 (5% of floor area — minimum for effective ventilation)
                 Source: EN 16798-1:2019 Annex B, Table B.3
```

### Overheating Risk Classification

```python
def classify_risk(proxy_odh: float) -> str:
    """
    Classify overheating risk level from proxy ODH.
    Thresholds calibrated to EN 16798-1:2019 Category II limit of 100 ODH
    for naturally ventilated buildings (§6.3.4.2).

    proxy_odh is dimensionless (sum of normalised stress indices),
    scaled to approximate ODH equivalence based on Evola et al. 2017
    calibration for Mediterranean apartments.
    """
    if proxy_odh < 0.15:
        return "LOW"
    elif proxy_odh < 0.35:
        return "MEDIUM"
    elif proxy_odh < 0.60:
        return "HIGH"
    else:
        return "CRITICAL"
```

---

## 8. Stage 4 — Strategy Scoring Model (MAUT)

### File: `src/strategy_scorer.py`

### Methodology

Multi-Attribute Utility Theory (MAUT) scoring for 5 passive strategies.
For each strategy:

1. **Precondition check** (binary) — physical feasibility
2. **MAUT score** (0–100) — estimated ODH reduction if implemented

```
impact_score_s = 100 × Σ(w_{s,i} × μ_{s,i}(x_i)) / Σ(w_{s,i})

where:
  w_{s,i}      = weight of factor i for strategy s (from literature)
  μ_{s,i}(x_i) = fuzzy membership function value for input x_i (0–1)
  x_i          = raw input value for factor i
```

### Fuzzy Membership Function

```python
def linear_ramp(x: float, x_min: float, x_max: float) -> float:
    """
    Linear ramp membership function.
    Returns 0 at x <= x_min, 1 at x >= x_max, linear between.
    """
    if x <= x_min:
        return 0.0
    if x >= x_max:
        return 1.0
    return (x - x_min) / (x_max - x_min)
```

### Data Class

```python
@dataclass
class StrategyScore:
    strategy_name: str          # "shading" / "cross_ventilation" / "thermal_mass" /
                                # "night_purge" / "green_roof"
    precondition_met: str       # "YES" / "PARTIAL" / "NO"
    precondition_reason: str    # explanation of precondition result
    impact_score: float         # 0–100 (higher = more ODH reduction = higher priority)
    impact_level: str           # "HIGH" (>66) / "MEDIUM" (33–66) / "LOW" (<33)
    factor_scores: dict         # {factor_name: (raw_value, mu_value, weighted_contribution)}
    affected_element_ids: list[str]   # IFC GlobalIds of elements this strategy modifies
    key_driver: str             # name of the factor with highest weighted contribution
```

### Impact Level Thresholds

```python
def score_to_level(score: float) -> str:
    # Thresholds derived from Lapisa et al. 2018 Table 5:
    # strategies reducing ODH by >40% = HIGH, 20-40% = MEDIUM, <20% = LOW
    # Mapped to 0-100 scale proportionally.
    if score >= 66:
        return "HIGH"
    elif score >= 33:
        return "MEDIUM"
    else:
        return "LOW"
```

---

### Strategy 1: External Shading

#### Precondition

```
YES    if facade GHI_facade > 150 Wh/m² AND WWR > 0.15 AND orientation not N/NE
PARTIAL if facade GHI_facade > 100 Wh/m² OR WWR > 0.10
NO     otherwise

Source: Santamouris M. & Asimakopoulos D. 1996, Passive Cooling of Buildings,
James & James, Chapter 4, §4.2:
"Solar shading is recommended when solar radiation on a facade exceeds
150 Wh/m² mean daily irradiance during the cooling season."
```

#### MAUT Factors and Weights

| Factor | Variable | Weight | Membership Function | Source |
|---|---|---|---|---|
| Summer façade GHI | GHI_facade (Wh/m²) | **0.40** | linear_ramp(x, 100, 350) | Lapisa et al. 2018, Table 3 — highest sensitivity parameter |
| Window-to-wall ratio | WWR (0–1) | **0.31** | linear_ramp(x, 0.10, 0.50) | Lapisa et al. 2018, Table 3 |
| Facade orientation | orientation_label | **0.29** | lookup table below | Szokolay 2004, Table 2.3 |

```python
SHADING_ORIENTATION_MU = {
    "N": 0.00, "NE": 0.20, "E": 0.50,
    "SE": 0.75, "S": 0.85, "SW": 1.00,
    "W": 0.75, "NW": 0.30
}
# SW and W prioritised for Barcelona: peak afternoon solar 14:00–18:00 July
# Source: Szokolay 2004 §2.3 + pvlib sun path at lat 41.3°N
```

#### Score Calculation

```python
def score_shading(facade: FacadeFeature, context: SiteContext) -> StrategyScore:
    ghi = get_facade_summer_ghi(facade.orientation_label, ...)  # Stage 3 helper
    wwr = facade.wwr
    orientation_mu = SHADING_ORIENTATION_MU[facade.orientation_label]

    factors = {
        "facade_GHI":  (ghi,              linear_ramp(ghi, 100, 350),  0.40),
        "WWR":         (wwr,              linear_ramp(wwr, 0.10, 0.50), 0.31),
        "orientation": (orientation_mu,   orientation_mu,               0.29),
    }
    score = 100 * sum(mu * w for _, mu, w in factors.values())
    # Evaluate per facade — return the facade with highest score as primary recommendation
```

#### Affected Elements

`facade.element_id` + `facade.window_element_ids`

---

### Strategy 2: Cross-Ventilation

#### Precondition

```
YES    if has_opposing_openings=True AND D/H <= 5.0 AND v_canyon >= 0.5 m/s
PARTIAL if has_opposing_openings=False (openings could be added) AND D/H <= 5.0
         OR has_opposing_openings=True AND v_canyon < 0.5 m/s
NO     if D/H > 5.0 (physically impossible regardless of openings)

Source: CIBSE AM10:2005 Natural Ventilation in Non-Domestic Buildings, §3.4:
"Single-sided ventilation is effective up to 2× room height depth.
Cross-ventilation is effective up to 5× floor-to-ceiling height depth."

D = building_depth_m (from Stage 1)
H = floor_to_ceiling_height_m (from Stage 1)
```

#### MAUT Factors and Weights

| Factor | Variable | Weight | Membership Function | Source |
|---|---|---|---|---|
| Canyon-corrected wind speed | v_canyon (m/s) | **0.35** | linear_ramp(x, 0.5, 3.5) | Santamouris 1996 Table 8.3 |
| Building depth/height ratio | D/H | **0.30** | inverse_ramp(x, 2.0, 5.0)* | CIBSE AM10:2005 §3.4 |
| Inlet area / floor area | A_inlet/A_floor | **0.20** | linear_ramp(x, 0.02, 0.10) | EN 16798-1:2019 Annex B, Table B.3 |
| Opposing outlet present | binary | **0.15** | 1.0 if True, 0.0 if False | Givoni 1994, Chapter 3 |

```
*inverse_ramp: compliance decreases as D/H increases
inverse_ramp(x, x_good, x_bad) = 1 - linear_ramp(x, x_good, x_bad)
```

```python
v_canyon = context.summer_mean_wind_m_s * context.canyon_wind_correction
dh_ratio = building.building_depth_m / building.floor_to_ceiling_height_m
inlet_ratio = building.operable_window_area_m2 / building.total_floor_area_m2
```

#### Affected Elements

All `IfcWall` element_ids on facades that lack openings (if PARTIAL) +
all `IfcWindow` element_ids (if openings need to be enlarged).
Add note: "Consider adding IfcWindow on [opposing_facade] facade to complete ventilation path."

---

### Strategy 3: Thermal Mass

#### Precondition

```
YES    if construction_mass = "heavy" OR (construction_mass = "medium" AND diurnal_swing > 6°C)
PARTIAL if construction_mass = "medium" OR (construction_mass = "lightweight" AND diurnal_swing > 8°C)
NO     if construction_mass = "lightweight" AND diurnal_swing < 6°C
       (thermal mass cannot be retrofitted cost-effectively; insufficient day-night swing
        means stored heat cannot be discharged)

Source: Givoni B. 1994, Passive and Low Energy Cooling of Buildings,
Van Nostrand Reinhold, Chapter 6:
"Thermal mass is effective when diurnal temperature range exceeds 10°C.
Partial effectiveness from 5°C. Below 5°C, thermal mass provides negligible benefit."

Note: Barcelona July diurnal swing from EPW = 6.54°C → PARTIAL to MEDIUM range.
This is an honest limitation of the Barcelona climate for this strategy.
```

#### MAUT Factors and Weights

| Factor | Variable | Weight | Membership Function | Source |
|---|---|---|---|---|
| Diurnal temperature swing | ΔT_diurnal (°C) | **0.40** | linear_ramp(x, 5.0, 15.0) | Balaras 1996, Energy and Buildings 24(3):179–195 |
| Construction thermal mass | mass_score (0–1) | **0.35** | direct (MASS_SCORE mapping) | ISO 13786:2017 thermal admittance |
| Building use / internal gains | IHG_proxy | **0.25** | lookup below | EN ISO 52016-1:2017 §B.4 |

```python
IHG_PROXY = {
    "residential": 0.35,   # lower internal gains, mass more effective at night cooling
    "office":      0.65,   # higher daytime gains, mass absorbs more
    "mixed":       0.50
}
# Source: EN ISO 52016-1:2017 Annex B, Table B.4 — default internal heat gain schedules

mass_score = MASS_SCORE[construction_mass]  # 0.0 / 0.5 / 1.0
delta_T = context.july_diurnal_swing_C      # 6.54°C for Barcelona EPW
ihg = IHG_PROXY[building_use]
```

#### Affected Elements

All `IfcWall` and `IfcSlab` elements where `construction_mass` is lightweight or medium.
Recommendation: "Increase thermal mass of [element_id] — consider replacing lightweight
partition with concrete block or rammed earth."

---

### Strategy 4: Night Purge Ventilation

#### Precondition

```
YES    if night_purge_hours_below_22C >= 150 AND operable_window_area > 0.05 × floor_area
PARTIAL if night_purge_hours_below_22C >= 75 OR operable_window_area between 0.02–0.05 × floor_area
NO     if night_purge_hours_below_22C < 50 (climate too warm for effective night cooling)

Source: Santamouris M. & Asimakopoulos D. 1996, Passive Cooling of Buildings,
James & James, Chapter 9, §9.3:
"Night ventilation requires at least 3–4°C difference between night outdoor and
indoor temperatures for a minimum of 6 hours per night to be effective."

IMPORTANT NOTE: Barcelona EPW gives only 104 summer night hours below 22°C.
This strategy will score LOW to MEDIUM for most Barcelona sites.
This is a CORRECT result reflecting the Mediterranean coastal climate — do not
adjust thresholds to artificially inflate this score.
```

#### MAUT Factors and Weights

| Factor | Variable | Weight | Membership Function | Source |
|---|---|---|---|---|
| Available cooling hours | hours_below_22C | **0.45** | linear_ramp(x, 50, 300) | Santamouris 1996 §9.3, primary determinant |
| Operable opening ratio | A_op/A_floor | **0.30** | linear_ramp(x, 0.02, 0.10) | CIBSE TM52:2013 §4.2 |
| Thermal mass to absorb day heat | mass_score | **0.25** | direct (MASS_SCORE mapping) | Balaras 1996 — night purge only effective with sufficient mass |

```python
hours = context.night_purge_hours_below_22C  # 104 for Barcelona
op_ratio = building.operable_window_area_m2 / building.total_floor_area_m2
mass = MASS_SCORE[dominant_construction_mass]
```

#### Affected Elements

All `IfcWindow` element_ids where `OperationType` is fixed (not operable).
Recommendation: "Replace fixed glazing on [element_id] with operable units
to enable night ventilation. Target: >5% of floor area operable."

---

### Strategy 5: Green Roof

#### Precondition

```
YES    if roof.is_exposed = True AND roof.area_m2 / total_floor_area_m2 >= 0.3
PARTIAL if roof.is_exposed = True AND roof area ratio < 0.3
        OR roof is partially shaded by taller adjacent buildings
NO     if roof.is_exposed = False (covered by upper floors) OR SVF_roof < 0.2

Source: Santamouris M. 2014, "Cooling the cities — a review of reflective and green
roof mitigation technologies to fight heat island and improve comfort in urban environments",
Solar Energy 103:682–703:
"Green roof effectiveness scales with exposed roof area and incoming solar radiation.
Minimum roof SVF of 0.2 required for meaningful evapotranspiration cooling effect."
```

#### MAUT Factors and Weights

| Factor | Variable | Weight | Membership Function | Source |
|---|---|---|---|---|
| Roof solar exposure (SVF) | svf_roof (0–1) | **0.40** | linear_ramp(x, 0.2, 1.0) | Santamouris 2014, Fig. 4 |
| Thermal comfort zone severity | gridcode (1–6) | **0.35** | (gridcode-1)/5 | Getter & Rowe 2006, Landscape Urban Plan. 77(3):217–229 |
| Roof area / total floor area | ratio | **0.25** | linear_ramp(x, 0.1, 0.5) | Santamouris 2014 §4.1 |

```python
svf_roof = context.svf_mean   # use site SVF as proxy for roof SVF
gridcode = context.thermal_comfort_gridcode
roof_ratio = building.roof.area_m2 / building.total_floor_area_m2
```

#### Affected Elements

`roof.element_id`
Recommendation: "Apply green roof substrate and planting to IfcSlab [element_id].
Minimum substrate depth 100mm for sedum mat; 200mm for herbaceous mix.
Estimated roof U-value after green roof: 0.15–0.25 W/m²K."

---

### Final Ranking

```python
def rank_strategies(scores: list[StrategyScore]) -> list[StrategyScore]:
    """
    Rank strategies by impact_score descending.
    Strategies with precondition_met="NO" are excluded from recommendations
    but included in report with explanation.
    Higher score = more ODH reduction = higher implementation priority.
    """
    viable = [s for s in scores if s.precondition_met != "NO"]
    excluded = [s for s in scores if s.precondition_met == "NO"]
    viable.sort(key=lambda s: s.impact_score, reverse=True)
    return viable + excluded
```

---

## 9. Stage 5 — LLM Recommendation Generation with GraphRAG

### File: `src/recommender.py`

### Architecture

Two components work together:

1. **GraphRAG** — retrieves relevant knowledge subgraph + document chunks
2. **Anthropic API** — generates geometric recommendations using retrieved context

### GraphRAG Overview

The knowledge graph has strategy nodes connected to literature, design options,
and IFC element types. When generating a recommendation for strategy S, the
retriever walks the graph from node S to collect:
- Justification passages from literature (from ChromaDB vector store)
- Design variants available for that strategy
- Relationships to other strategies (synergies and conflicts)
- Quantitative thresholds from standards

See Section 12 for full graph specification.

### Anthropic API Call

```python
import anthropic
import json

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

def generate_recommendation(
    strategy_score: StrategyScore,
    building: BuildingFeatures,
    context: SiteContext,
    diagnosis: ThermalDiagnosis,
    retrieved_context: str,   # from GraphRAG retrieval
    all_scores: list[StrategyScore]
) -> str:
    """
    Generate a detailed geometric recommendation for one strategy.
    Uses claude-sonnet-4-20250514 for balance of quality and speed.
    """
    prompt = build_recommendation_prompt(
        strategy_score, building, context, diagnosis,
        retrieved_context, all_scores
    )
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

See Section 13 for prompt templates.

---

## 10. User Inputs and Outputs

### Inputs

#### Required

| Input | Type | Description |
|---|---|---|
| `ifc_path` | file path | Path to the .ifc file |
| `site_lat` | float | Site latitude (decimal degrees) |
| `site_lon` | float | Site longitude (decimal degrees) |
| `building_use` | string | `"residential"` / `"office"` / `"mixed"` |

#### Optional (with defaults)

| Input | Type | Default | Description |
|---|---|---|---|
| `shgc` | float | 0.6 | Solar heat gain coefficient of glazing |
| `output_dir` | path | `outputs/reports/` | Where to write the report |

### CLI Usage

```bash
python main.py \
  --ifc path/to/building.ifc \
  --lat 41.3851 \
  --lon 2.1734 \
  --use residential \
  --output outputs/reports/
```

### Outputs

#### 1. Console Summary (printed during run)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PASSIVE DESIGN ADVISOR — Barcelona 2025
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SITE: 41.3851°N, 2.1734°E
THERMAL COMFORT ZONE: 5 — Low (high heat stress area)
OVERHEATING RISK: HIGH (proxy ODH = 0.48)

STRATEGY RECOMMENDATIONS (ranked by impact):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. EXTERNAL SHADING       │ HIGH   │ Score: 82/100 │ FEASIBLE
2. CROSS-VENTILATION      │ HIGH   │ Score: 74/100 │ FEASIBLE
3. GREEN ROOF             │ MEDIUM │ Score: 55/100 │ FEASIBLE
4. THERMAL MASS           │ MEDIUM │ Score: 48/100 │ FEASIBLE
5. NIGHT PURGE            │ LOW    │ Score: 28/100 │ PARTIAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 2. JSON Report (`report.json`)

```json
{
  "metadata": {
    "ifc_file": "building.ifc",
    "site_lat": 41.3851,
    "site_lon": 2.1734,
    "thermal_comfort_zone": 5,
    "overheating_risk": "HIGH",
    "proxy_odh": 0.48,
    "generated_at": "2025-05-17T14:32:00"
  },
  "building_summary": {
    "total_floor_area_m2": 450.0,
    "number_of_floors": 3,
    "floor_to_ceiling_height_m": 2.8,
    "building_depth_m": 14.0,
    "dominant_construction_mass": "medium"
  },
  "strategies": [
    {
      "rank": 1,
      "name": "external_shading",
      "precondition_met": "YES",
      "precondition_reason": "South facade GHI = 312 Wh/m² exceeds 150 Wh/m² threshold. WWR = 0.38.",
      "impact_score": 82.0,
      "impact_level": "HIGH",
      "affected_elements": ["2O3Pk8Qv5EexTLp9ArZ4Jd", "1Q5Lm2Rv8HhyXBn7CwA1Fe"],
      "key_driver": "facade_GHI",
      "factor_scores": {
        "facade_GHI": {"raw": 312.0, "mu": 0.88, "weighted": 0.352},
        "WWR":        {"raw": 0.38,  "mu": 0.70, "weighted": 0.217},
        "orientation":{"raw": "SW",  "mu": 1.00, "weighted": 0.290}
      },
      "recommendation": "...(LLM generated text)..."
    }
  ]
}
```

#### 3. Markdown Report (`report.md`)

Human-readable version of the JSON report with full LLM-generated geometric
recommendations, design options, and literature citations. Format:

```markdown
# Passive Design Advisor Report
## [Building name from IFC] — [date]

### Site Analysis
...

### Overheating Diagnosis
...

### Recommendations

#### 1. External Shading — HIGH Impact (82/100)
**Affected elements:** South facade wall (IFC ID: 2O3Pk8...), Windows (IFC IDs: 1Q5Lm2...)

**Why this strategy:** ...LLM text with citations...

**Design options:**
- Option A: Fixed horizontal louvers — [description]
- Option B: Operable external blinds — [description]
- Option C: Vegetated trellis — [description]

**Geometric changes required:** ...LLM text referencing element IDs...
```

---

## 11. Data Dependencies and File Paths

### Required files (must exist before running)

| File | Path | Used in stage |
|---|---|---|
| EPW weather file | `data/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw` | 2, 3 |
| EPW summary JSON | `outputs/epw_summary.json` | 2 (run parse_epw.py first) |
| ICGC buildings | `data/Base_-_Alçades.gpkg` | 2 |
| Thermal comfort zones | `data/confort_termic_od.gpkg` | 2 |
| Strategy graph | `graph/strategy_graph.json` | 5 (run build_graph.py first) |
| ChromaDB store | `graph/chroma_db/` | 5 (run build_rag.py first) |

### Coordinate reference systems

| Dataset | Native CRS | Convert to |
|---|---|---|
| ICGC Alçades | EPSG:25831 | EPSG:25831 (keep) |
| confort_termic_od | EPSG:25831 | EPSG:25831 (keep) |
| User site coordinates (lat/lon) | EPSG:4326 | EPSG:25831 for spatial ops |

```python
from pyproj import Transformer
transformer = Transformer.from_crs("EPSG:4326", "EPSG:25831", always_xy=True)
x, y = transformer.transform(site_lon, site_lat)
site_point_25831 = Point(x, y)
```

---

## 12. GraphRAG Knowledge Base Specification

### File: `scripts/build_graph.py` and `scripts/build_rag.py`

### Graph Structure (NetworkX)

```python
import networkx as nx

G = nx.DiGraph()
```

#### Node Types and Required Nodes

**Strategy nodes** (5 total):
```python
for strategy in ["shading", "cross_ventilation", "thermal_mass", "night_purge", "green_roof"]:
    G.add_node(strategy, type="strategy", label=strategy)
```

**Design option nodes** — add all of these:

```python
DESIGN_OPTIONS = {
    "shading": [
        {"id": "shading_fixed_louvers",
         "label": "Fixed horizontal louvers",
         "description": "Permanent horizontal fins above windows. Best for south facades. Sized for latitude 41°N to block summer sun above 60° altitude while admitting winter sun below 30°. Overhang depth = window height × tan(90° - 60° - lat).",
         "suitable_for": ["S", "SE", "SW"],
         "performance_note": "Reduces solar heat gain by 50–80% on south facades. Source: Szokolay 2004 §3.4."},
        {"id": "shading_operable_blinds",
         "label": "External operable blinds or shutters",
         "description": "User-controlled external roller blinds or venetian shutters. More flexible than fixed louvers — can be opened in winter or for daylight. Requires maintenance. Best for E and W facades where sun angle varies.",
         "suitable_for": ["E", "W", "SE", "SW"],
         "performance_note": "Can reduce solar gain by up to 90% when closed. Source: CIBSE Guide A 2015, Table 6.5."},
        {"id": "shading_vegetated_trellis",
         "label": "Vegetated trellis / green facade",
         "description": "Climbing plants on a structural frame 200–400mm from facade surface. Provides shading AND evapotranspiration cooling effect. Deciduous species preferred — shade in summer, solar access in winter. Suitable for all orientations receiving sufficient solar radiation for plant growth.",
         "suitable_for": ["S", "SE", "SW", "E", "W"],
         "performance_note": "Reduces surface temperature by 5–15°C and ambient by 1–3°C. Source: Pérez et al. 2011, Renewable and Sustainable Energy Reviews 15(1):576–583."},
        {"id": "shading_overhangs",
         "label": "Roof overhangs / cantilevered balconies",
         "description": "Horizontal projection from the building facade. Most effective on south facade at Barcelona latitude. Depth calculated using solar angle geometry: D = H_window × tan(90° - solar_altitude_summer_noon). At lat 41°N, summer noon altitude ≈ 72°, so D ≈ H × 0.32.",
         "suitable_for": ["S", "SE", "SW"],
         "performance_note": "Fixed geometry — calculate depth precisely for latitude. Source: Szokolay 2004 §3.4.2."},
    ],
    "cross_ventilation": [
        {"id": "cv_through_building",
         "label": "Through-building cross-ventilation",
         "description": "Open windows on windward and leeward facades simultaneously. Inlet on prevailing wind side (NE/N for Barcelona), outlet on opposite side. Inlet area should be 60–70% of outlet area for optimal flow. Source: CIBSE AM10:2005 §3.3.",
         "suitable_for": "buildings with D/H < 5",
         "performance_note": "Achieves 5–15 ACH under moderate wind. Most effective strategy for Barcelona's coastal wind regime."},
        {"id": "cv_courtyard",
         "label": "Internal courtyard for ventilation",
         "description": "Central courtyard creates pressure differential driving cross-ventilation from perimeter to core. Works even in calm wind conditions through thermal buoyancy. Courtyard width : height ratio should be 1:1 to 2:1.",
         "suitable_for": "deep plan buildings D/H > 3",
         "performance_note": "Extends effective ventilation depth beyond CIBSE 5×H limit. Source: Santamouris 1996 Ch.8."},
        {"id": "cv_wing_walls",
         "label": "Wing walls to direct airflow",
         "description": "Vertical fins flanking windows on windward facade to capture and redirect oblique wind into openings. Effective when prevailing wind is oblique to facade. Fin projection = 0.5–1.0 × window width.",
         "suitable_for": "facades where wind is oblique (>30° from normal)",
         "performance_note": "Increases inlet velocity by 30–50%. Source: Givoni 1994 Ch.4."},
    ],
    "thermal_mass": [
        {"id": "tm_exposed_concrete",
         "label": "Exposed concrete or masonry internal surfaces",
         "description": "Leave internal face of concrete walls or floor slabs unfinished or with thin plaster only. Insulation must be placed externally. Minimum 150mm concrete thickness for effective thermal lag. Thermal admittance > 3 W/m²K required.",
         "performance_note": "Shifts peak indoor temperature by 4–6 hours. Source: Balaras 1996 §3."},
        {"id": "tm_pcm",
         "label": "Phase change material (PCM) panels",
         "description": "Microencapsulated PCM integrated into plasterboard or ceiling tiles. Melting point selected at 23–26°C for Barcelona summer conditions. Provides equivalent thermal mass in lightweight construction. Typical capacity: 14–30 MJ/m³.",
         "performance_note": "Reduces peak temperature by 2–4°C in lightweight buildings. Source: Cabeza et al. 2011, Energy and Buildings 43(6):1523–1533."},
        {"id": "tm_trombe_wall",
         "label": "Trombe wall (thermal storage wall)",
         "description": "South-facing heavy masonry wall (300–400mm) with glazing 50–150mm in front. Glazing admits solar radiation; mass absorbs and releases heat on delay. Include ventilation openings top and bottom for convective heating in winter. In Barcelona, include summer shading to prevent overheating.",
         "performance_note": "Effective for winter heating. In summer MUST be shaded to avoid overheating. Source: Szokolay 2004 §4.5."},
    ],
    "night_purge": [
        {"id": "np_operable_windows",
         "label": "Secure operable windows for night ventilation",
         "description": "Replace fixed glazing with tilt-and-turn or pivot windows. Install lockable ventilation position (10–15° opening) for security. Inlet openings near floor level, outlet near ceiling for thermal stratification. Target: >5% of floor area operable.",
         "performance_note": "Reduces next-day peak temperature by 2–4°C when outdoor temp < 22°C. Source: CIBSE TM52:2013 §4.2."},
        {"id": "np_roof_ventilators",
         "label": "Automated roof ventilators / clerestory openings",
         "description": "Motorised roof vents or high-level clerestory windows open automatically when outdoor temperature drops below setpoint (22°C) after sunset. Stack effect assists flow even in calm conditions. Controls: temperature sensor + BMS or simple thermostat.",
         "performance_note": "Stack ventilation adds 1–3 ACH even at zero wind. Source: Santamouris 1996 §9.4."},
        {"id": "np_cool_tower",
         "label": "Wind tower / cool tower",
         "description": "Vertical tower above roof captures wind and directs it downward into the building. Traditional Malqaf design adapted for Mediterranean climate. Combine with night operation only (close during hot afternoons). Effective in Barcelona's sea breeze regime.",
         "performance_note": "Passive — no energy consumption. Effective when wind speed > 1.5 m/s. Source: Givoni 1994 Ch.9."},
    ],
    "green_roof": [
        {"id": "gr_sedum_mat",
         "label": "Extensive sedum mat (50–100mm substrate)",
         "description": "Lightweight (60–120 kg/m²), low maintenance, drought-tolerant sedum species. Minimum substrate depth 50mm. Structural requirement low — suitable for most existing roofs. Limited plant diversity. Irrigation not required after establishment.",
         "performance_note": "Reduces roof surface temperature by 20–30°C vs bare membrane. Reduces heat flux into building by 60–90%. Source: Getter & Rowe 2006 §4."},
        {"id": "gr_herbaceous",
         "label": "Semi-intensive herbaceous green roof (150–250mm)",
         "description": "Medium substrate depth, wider plant palette including grasses and perennials. Better evapotranspiration performance than sedum. Requires occasional maintenance and irrigation in Barcelona's dry summers. Load: 120–200 kg/m².",
         "performance_note": "Better thermal performance than extensive roof, especially in dry summers due to irrigation. Source: Santamouris 2014 §5.2."},
        {"id": "gr_combined_pv",
         "label": "Green roof combined with photovoltaic panels",
         "description": "Bifacial PV panels elevated 300–500mm above green roof substrate. Green roof reduces ambient temperature around panels (improves PV efficiency by 3–5%). PV panels shade substrate (reduces irrigation need). Synergistic system.",
         "performance_note": "Dual benefit: thermal comfort + renewable energy. Source: Chemisana & Lamnatou 2014, Applied Energy 119:47–54."},
    ]
}
```

**Literature / standard nodes:**
```python
LITERATURE_NODES = [
    {"id": "EN16798_1",         "type": "standard",  "label": "EN 16798-1:2019"},
    {"id": "ASHRAE55_2023",     "type": "standard",  "label": "ASHRAE 55:2023"},
    {"id": "CIBSE_AM10",        "type": "standard",  "label": "CIBSE AM10:2005"},
    {"id": "CIBSE_TM52",        "type": "standard",  "label": "CIBSE TM52:2013"},
    {"id": "ISO13786",          "type": "standard",  "label": "ISO 13786:2017"},
    {"id": "santamouris_1996",  "type": "paper",     "label": "Santamouris 1996"},
    {"id": "givoni_1994",       "type": "paper",     "label": "Givoni 1994"},
    {"id": "balaras_1996",      "type": "paper",     "label": "Balaras 1996"},
    {"id": "lapisa_2018",       "type": "paper",     "label": "Lapisa et al. 2018"},
    {"id": "evola_2017",        "type": "paper",     "label": "Evola et al. 2017"},
    {"id": "szokolay_2004",     "type": "paper",     "label": "Szokolay 2004"},
    {"id": "blocken_2007",      "type": "paper",     "label": "Blocken et al. 2007"},
    {"id": "santamouris_2014",  "type": "paper",     "label": "Santamouris 2014"},
    {"id": "getter_rowe_2006",  "type": "paper",     "label": "Getter & Rowe 2006"},
]
```

#### Edge Types

```python
# strategy → has_variant → design_option
G.add_edge("shading", "shading_fixed_louvers",    relation="has_variant")
G.add_edge("shading", "shading_operable_blinds",  relation="has_variant")
G.add_edge("shading", "shading_vegetated_trellis", relation="has_variant")
G.add_edge("shading", "shading_overhangs",        relation="has_variant")
# (repeat for all design options)

# strategy → justified_by → literature
G.add_edge("shading",            "lapisa_2018",      relation="justified_by", note="factor weights from Table 3")
G.add_edge("shading",            "szokolay_2004",    relation="justified_by", note="orientation weights §2.3")
G.add_edge("shading",            "santamouris_1996", relation="justified_by", note="GHI threshold §4.2")
G.add_edge("cross_ventilation",  "CIBSE_AM10",       relation="justified_by", note="D/H limit §3.4")
G.add_edge("cross_ventilation",  "santamouris_1996", relation="justified_by", note="wind speed weights Table 8.3")
G.add_edge("cross_ventilation",  "givoni_1994",      relation="justified_by", note="opposing outlets Ch.3")
G.add_edge("cross_ventilation",  "blocken_2007",     relation="justified_by", note="canyon correction Table 3")
G.add_edge("thermal_mass",       "balaras_1996",     relation="justified_by", note="diurnal swing weights")
G.add_edge("thermal_mass",       "givoni_1994",      relation="justified_by", note="diurnal swing threshold Ch.6")
G.add_edge("thermal_mass",       "ISO13786",         relation="justified_by", note="mass classification")
G.add_edge("night_purge",        "santamouris_1996", relation="justified_by", note="cooling hours threshold §9.3")
G.add_edge("night_purge",        "CIBSE_TM52",       relation="justified_by", note="opening area §4.2")
G.add_edge("green_roof",         "santamouris_2014", relation="justified_by", note="SVF threshold §4.1")
G.add_edge("green_roof",         "getter_rowe_2006", relation="justified_by", note="gridcode weights")

# strategy synergies
G.add_edge("thermal_mass",  "night_purge",       relation="synergy_with",
           note="Thermal mass absorbs daytime heat; night purge discharges it. Combined effect > sum of parts. Source: Balaras 1996 §4.")
G.add_edge("shading",       "cross_ventilation", relation="synergy_with",
           note="Shading reduces solar gain, lowering indoor temp, increasing ventilation effectiveness. Source: Evola et al. 2017.")

# strategy conflicts
G.add_edge("thermal_mass",  "cross_ventilation", relation="no_conflict",
           note="Compatible — heavy construction does not impede ventilation.")
G.add_edge("shading",       "thermal_mass",      relation="no_conflict",
           note="Compatible — shading reduces peak load that mass must handle.")
```

### ChromaDB Vector Store

**File: `scripts/build_rag.py`**

```python
import chromadb
from sentence_transformers import SentenceTransformer
import os, json

CHROMA_PATH = "graph/chroma_db"
CHUNKS_PATH = "data/rag_documents/chunks"

def build_rag():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    collection = client.get_or_create_collection("passive_design_knowledge")

    for filename in os.listdir(CHUNKS_PATH):
        if not filename.endswith(".json"):
            continue
        with open(os.path.join(CHUNKS_PATH, filename)) as f:
            chunks = json.load(f)
        for chunk in chunks:
            embedding = model.encode(chunk["text"]).tolist()
            collection.add(
                ids=[chunk["id"]],
                embeddings=[embedding],
                documents=[chunk["text"]],
                metadatas=[{
                    "source": chunk["source"],
                    "strategy": chunk.get("strategy", "general"),
                    "page": chunk.get("page", ""),
                }]
            )
```

#### Document Chunks Format

Each file in `data/rag_documents/chunks/` is a JSON array:

```json
[
  {
    "id": "lapisa_2018_chunk_001",
    "source": "Lapisa et al. 2018 — Optimisation of overheating mitigation strategies",
    "strategy": "shading",
    "page": "Table 3",
    "text": "Sensitivity analysis of passive cooling strategies for a Mediterranean residential building showed that solar shading was the most effective single measure, responsible for 38–42% of total cooling load reduction. Window-to-wall ratio was the second most sensitive parameter (29–33%), followed by facade orientation (25–29%). These weights were derived from parametric EnergyPlus simulations varying each parameter independently while holding others constant."
  }
]
```

#### Retrieval Function

```python
def retrieve_for_strategy(
    strategy_name: str,
    graph: nx.DiGraph,
    collection,
    model,
    n_results: int = 5
) -> str:
    """
    1. Walk graph from strategy node to collect justified_by literature labels
    2. Query ChromaDB with strategy name + design option descriptions
    3. Return formatted context string for LLM prompt
    """
    # Graph walk
    graph_context = []
    for _, neighbor, data in graph.out_edges(strategy_name, data=True):
        node_data = graph.nodes[neighbor]
        relation = data.get("relation", "")
        if relation == "justified_by":
            graph_context.append(f"Justified by {node_data['label']}: {data.get('note','')}")
        elif relation == "has_variant":
            graph_context.append(f"Design option: {node_data['label']} — {node_data.get('description','')}")
        elif relation == "synergy_with":
            graph_context.append(f"Synergy with {neighbor}: {data.get('note','')}")

    # Vector retrieval
    query = f"{strategy_name} passive cooling Barcelona Mediterranean"
    results = collection.query(
        query_embeddings=[model.encode(query).tolist()],
        n_results=n_results,
        where={"strategy": {"$in": [strategy_name, "general"]}}
    )
    doc_context = "\n---\n".join(results["documents"][0])

    return "KNOWLEDGE GRAPH CONTEXT:\n" + "\n".join(graph_context) + \
           "\n\nLITERATURE CONTEXT:\n" + doc_context
```

---

## 13. LLM Prompt Templates

### System Prompt

```python
SYSTEM_PROMPT = """You are a passive building design advisor specialising in
Mediterranean climates, specifically Barcelona, Spain. You help architects
improve thermal comfort in the design phase of new buildings.

Your role is to generate specific, geometric, actionable recommendations that
reference the architect's actual building model elements by their IFC element IDs.

Rules:
1. Always reference specific IFC element IDs when describing changes needed
2. Always cite the literature source that justifies each recommendation
3. Always provide 2–3 design options (not just one) with brief pros/cons
4. Be quantitative where possible: give dimensions, ratios, depths, areas
5. Acknowledge limitations honestly — if Barcelona's climate limits the
   effectiveness of a strategy (e.g. night purge), say so explicitly
6. Keep each recommendation to 250–350 words
7. Do not recommend active mechanical systems — passive design only
8. Do not assess regulatory compliance or issue certifications"""
```

### Recommendation Prompt Template

```python
def build_recommendation_prompt(
    score: StrategyScore,
    building: BuildingFeatures,
    context: SiteContext,
    diagnosis: ThermalDiagnosis,
    retrieved_context: str,
    all_scores: list[StrategyScore]
) -> str:

    synergy_strategies = [
        s.strategy_name for s in all_scores
        if s.strategy_name != score.strategy_name
        and s.impact_level in ["HIGH", "MEDIUM"]
        and s.precondition_met != "NO"
    ]

    return f"""
BUILDING CONTEXT:
- IFC file: {building.ifc_file_path}
- Building use: {building.building_use}
- Total floor area: {building.total_floor_area_m2:.0f} m²
- Floors: {building.number_of_floors}
- Floor-to-ceiling height: {building.floor_to_ceiling_height_m:.1f} m
- Building depth: {building.building_depth_m:.1f} m
- Dominant construction: {building.facades[0].construction_mass}

SITE CONTEXT:
- Thermal comfort zone: {context.thermal_comfort_gridcode} ({context.thermal_comfort_label})
- Sky view factor: {context.svf_mean:.2f}
- Canyon H/W ratio: {context.canyon_hw_ratio:.1f}
- Canyon wind correction: {context.canyon_wind_correction}
- Summer mean wind speed (EPW): {context.summer_mean_wind_m_s:.1f} m/s
- Canyon-corrected wind: {context.summer_mean_wind_m_s * context.canyon_wind_correction:.1f} m/s
- July diurnal swing: {context.july_diurnal_swing_C:.1f}°C
- Summer CDH above 26°C: {context.summer_CDH_above_26C:.0f}

THERMAL DIAGNOSIS:
- Overheating risk: {diagnosis.overheating_risk_level}
- Proxy ODH: {diagnosis.estimated_proxy_ODH:.2f}
- Critical facades (element IDs): {', '.join(diagnosis.critical_facades)}

STRATEGY TO RECOMMEND: {score.strategy_name.upper().replace('_', ' ')}
- Impact score: {score.impact_score:.0f}/100
- Impact level: {score.impact_level}
- Precondition: {score.precondition_met} — {score.precondition_reason}
- Affected IFC elements: {', '.join(score.affected_element_ids)}
- Key driver factor: {score.key_driver}
- Factor breakdown: {json.dumps(score.factor_scores, indent=2)}

OTHER VIABLE STRATEGIES (for synergy mentions):
{', '.join(synergy_strategies)}

RETRIEVED KNOWLEDGE:
{retrieved_context}

TASK:
Write a recommendation for implementing {score.strategy_name.replace('_', ' ')} on this
specific building. Structure your response as follows:

1. WHY THIS STRATEGY (2–3 sentences, cite the key driver factor and its value,
   reference the relevant standard or paper from the retrieved context)

2. AFFECTED ELEMENTS (list the IFC element IDs and what each represents)

3. DESIGN OPTIONS (2–3 options with:
   - name and brief description
   - specific dimensions or parameters for this building
   - pros and cons for this specific site)

4. GEOMETRIC CHANGES REQUIRED (specific instructions referencing element IDs,
   include dimensions where possible)

5. EXPECTED BENEFIT (quantified estimate of ODH reduction based on literature,
   acknowledge any limitations for Barcelona's specific climate)

6. SYNERGIES (if applicable, mention how this strategy combines with
   {', '.join(synergy_strategies[:2]) if synergy_strategies else 'other strategies'})
"""
```

---

## 14. Output Format Specification

### Report Filename Convention

```
outputs/reports/{ifc_filename_stem}_{timestamp}.json
outputs/reports/{ifc_filename_stem}_{timestamp}.md
```

### Markdown Report Structure

```markdown
# Passive Design Advisor Report
**Building:** {ifc_filename}
**Site:** {lat}°N, {lon}°E
**Generated:** {timestamp}
**Tool version:** 1.0.0

---

## Site Analysis

| Parameter | Value |
|---|---|
| Thermal comfort zone | {gridcode} — {label} |
| Sky view factor | {svf:.2f} |
| Canyon H/W ratio | {hw:.1f} |
| Dominant wind direction | {wind_dir} |
| Summer mean wind (EPW) | {wind_ms:.1f} m/s |
| Canyon-corrected wind | {wind_canyon:.1f} m/s |
| July diurnal swing | {swing:.1f}°C |
| Summer CDH >26°C | {cdh:.0f} |

---

## Building Summary

| Parameter | Value |
|---|---|
| Total floor area | {area:.0f} m² |
| Floors | {floors} |
| Floor-to-ceiling height | {h:.1f} m |
| Building depth | {depth:.1f} m |
| Dominant construction | {mass} |
| Opposing openings | {opposing} |

---

## Overheating Diagnosis

**Risk level:** {risk}
**Proxy ODH:** {odh:.2f}

{diagnosis_text}

**Critical elements:**
{list of element IDs with orientation and GHI}

---

## Strategy Recommendations

### 1. [Strategy Name] — [LEVEL] Impact (Score: X/100)

{full LLM recommendation text}

---
(repeat for each strategy)

---

## Excluded Strategies

### [Strategy Name] — NOT FEASIBLE
**Reason:** {precondition_reason}

---

## References

All thresholds and weights in this analysis are derived from the following
certified sources:

- EN 16798-1:2019 Energy performance of buildings — Part 1 (supersedes EN 15251)
- ASHRAE 55:2023 Thermal Environmental Conditions for Human Occupancy
- CIBSE AM10:2005 Natural Ventilation in Non-Domestic Buildings
- CIBSE TM52:2013 The Limits of Thermal Comfort
- Santamouris M. & Asimakopoulos D. 1996 — Passive Cooling of Buildings
- Givoni B. 1994 — Passive and Low Energy Cooling of Buildings
- Balaras C.A. 1996 — The role of thermal mass on the cooling load of buildings
- Lapisa R. et al. 2018 — Optimisation of overheating mitigation strategies
- Evola G. et al. 2017 — Natural ventilation in Mediterranean apartments
- Szokolay S.V. 2004 — Introduction to Architectural Science
- Blocken B. et al. 2007 — CFD simulations of wind flow over urban areas
- Santamouris M. 2014 — Cooling the cities: green roof review
- Getter K.L. & Rowe D.B. 2006 — The role of extensive green roofs
```

---

## 15. Validation and Testing

### Test IFC File

Download a representative IFC file from:
https://github.com/buildingSMART/Sample-Test-Files

Use `Duplex_A_20110907.ifc` (residential, multiple facades, varied WWR).
Expected behaviour:
- Shading should score HIGH for south/SW facades
- Cross-ventilation should score MEDIUM (depends on depth)
- Night purge should score LOW (Barcelona climate constraint)

### Unit Tests

Create `tests/test_scorer.py`:

```python
def test_shading_high_score():
    """South facade, high WWR should produce HIGH shading score."""
    # GHI_facade = 312 Wh/m², WWR = 0.45, orientation = SW
    # Expected score > 66

def test_night_purge_low_barcelona():
    """Barcelona's 104 night cooling hours should produce LOW night purge score."""
    # hours_below_22C = 104 → linear_ramp(104, 50, 300) = 0.216
    # Expected score < 33

def test_precondition_cross_vent_deep_plan():
    """Building depth > 5 × floor height should give precondition NO."""
    # building_depth = 18m, floor_height = 2.8m → D/H = 6.43 > 5.0
    # Expected precondition_met = "NO"

def test_svf_open_site():
    """No surrounding buildings → SVF should be 1.0."""

def test_thermal_comfort_zone_lookup():
    """Known coordinate in Eixample should return gridcode 4–6."""
    # Test coord: 41.3925°N, 2.1628°E (Eixample central)
```

### Validation Against Literature

After building is complete, validate against:

**Reference case:** Evola et al. 2017 Mediterranean apartment
- Summer mean temp ≈ 25°C, diurnal swing ≈ 8°C, WWR ≈ 0.30 south facade
- Expected tool output: shading HIGH, cross-ventilation HIGH, thermal mass MEDIUM,
  night purge LOW-MEDIUM, green roof MEDIUM
- Compare with Evola Table 4 strategy rankings — must be consistent in relative order

Document validation results in `docs/validation.md`.

---

*End of specification. All formulas, weights, and thresholds are mandatory —
do not substitute with alternative values without updating the reference citation.*
