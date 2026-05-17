# Passive Design Advisor — Dataset and Pipeline Summary

## 1. Project Goal

The tool helps architects in the early design phase visualize and evaluate passive design geometry interventions for a proposed building in central Barcelona.

The architect provides a **location** and a **simplified 3D building model or geometric inputs**. The tool combines this with climate, urban morphology, UHI, vegetation, and passive design knowledge to recommend which passive strategies are most suitable.

The tool does **not** aim to run a full energy simulation. It acts as an early-stage decision-support system that checks whether passive strategies are physically possible and estimates their likely impact.

---

## 2. Main User Inputs

| Input | Description | Purpose |
|---|---|---|
| Location | Address, coordinates, or map-selected point in Barcelona | Connects the project to climate, UHI, and urban morphology data |
| Simplified 3D model / geometry | Building massing, façade orientation, façade area, roof area, height | Defines the geometry to analyze |
| Window data | Window area, window-to-wall ratio, operable windows | Used for shading, solar gain, cross-ventilation, and night purge checks |
| Room / plan data | Room depth, plan depth, opposite openings | Used for natural ventilation potential |
| Envelope type | Lightweight, medium, or heavy construction | Used for thermal mass and night purge potential |
| Roof data | Roof type, roof area, roof exposure | Used for green roof potential |

For the MVP, the building geometry can be entered manually through a form or provided as a simplified JSON file. Later, it can be extracted from Rhino, Revit, IFC, or Speckle.

---

## 3. Dataset Summary Table

| Dataset | Priority | Format | Used For | Fed Into | Cleaning / Processing Needed |
|---|---|---|---|---|---|
| Barcelona EPW weather file | Essential | `.epw`, converted to `.csv` | Base climate: temperature, humidity, wind speed, wind direction, solar radiation | Climate processor → indicator builder → rule engine | Parse EPW, convert units if needed, extract summer months, calculate daily max/min temperature, night temperature drop, overheating hours, prevailing wind direction |
| User building geometry dataset | Essential | `.json`, `.csv`, IFC, Rhino/Grasshopper export, or manual form | Main design input: WWR, façade orientation, roof area, plan depth, openings, construction type | Geometry extractor → indicator builder → rule engine → visualization | Standardize units, calculate WWR, classify orientations, validate missing values, assign geometry IDs |
| Location dataset | Essential | Coordinates in `.json` or `.csv` | Links the selected building site to climate, UHI, and urban morphology layers | Map interface → spatial query module | Geocode address if needed, standardize CRS, store latitude/longitude |
| Building footprints | Essential | `.geojson`, `.shp`, or OSM extract | Surrounding building context, density, obstruction | Urban morphology processor → rule engine | Clip around selected location, reproject CRS, remove invalid geometries |
| Building heights / building levels | Essential | `.geojson`, `.shp`, OSM tags, or joined table | Urban canyon ratio, obstruction, shading potential, wind sheltering | Urban morphology processor → rule engine | Join height data to footprints, fill missing values, estimate height from building levels × 3 m if needed |
| Street network / street width | Useful | OSM roads, `.geojson`, `.shp` | Estimate canyon ratio and wind exposure | Urban morphology processor → rule engine | Extract nearby streets, estimate width from road type or distance between building façades |
| UHI / heat comfort layer | Important but optional for MVP | `.geojson`, `.shp`, raster, or municipal heat comfort dataset | Adjusts base EPW climate risk by neighborhood/local heat condition | UHI processor → indicator builder → rule engine | Clip/intersect with selected location, classify local heat risk, normalize to low/medium/high or 0–1 score |
| Vegetation / green cover | Optional but useful | `.geojson`, `.shp`, raster, NDVI, OSM green areas | Local cooling context, green roof justification, ecological layer | Urban context processor → rule engine | Clip around site, calculate green area ratio within buffer, classify vegetation availability |
| Passive strategy thresholds | Essential | `.csv` or `.json` | Core logic for scoring passive strategies | Rule-based scoring engine | Convert literature/design assumptions into thresholds, document source, add confidence level |
| Passive design papers / standards | Essential for RAG | PDF, TXT, Markdown | Evidence, justification, explanation, citations | RAG knowledge base → LLM explanation | Clean text, chunk documents, tag by topic: shading, ventilation, thermal mass, night purge, green roof, adaptive comfort |
| Reference cases | Useful | `.csv` or `.json` | Validation against known passive design scenarios | Validation module → final report | Standardize case geometry, expected strategy, tool output, match / mismatch |
| Synthetic training cases | Optional | `.csv` | Train a small decision tree or classifier | Optional ML model | Generate rule-based labels, encode categories, balance classes, split train/test |
| Visualization geometry dataset | Essential for visual output | `.json`, `.geojson`, GLTF, Rhino layers, Speckle objects | Colored façade, roof, and intervention visualization | Visualization layer | Match geometry IDs with strategy scores, simplify geometry, assign colors and intervention labels |

---

## 4. Climate Dataset: EPW

The **Barcelona EPW file** is the base climate dataset.

It provides hourly weather data that can be used to derive the main climate indicators required for passive design scoring.

### Variables from EPW

| EPW Variable | Used For |
|---|---|
| Dry bulb temperature | Overheating risk, adaptive comfort, night purge |
| Relative humidity | Comfort adjustment |
| Wind speed | Natural ventilation potential |
| Wind direction | Cross-ventilation alignment |
| Global horizontal radiation | General solar exposure |
| Direct normal radiation | Façade solar risk and shading need |
| Diffuse horizontal radiation | General sky radiation / daylight approximation |

### Derived Indicators

| Derived Indicator | Purpose |
|---|---|
| Summer overheating hours | Identifies heat stress periods |
| Daily maximum temperature | Measures daytime heat risk |
| Daily minimum temperature | Used for night cooling potential |
| Night temperature drop | Used for night purge ventilation scoring |
| Prevailing wind direction | Used for cross-ventilation potential |
| Solar exposure risk | Used for façade shading priority |

For the MVP, one Barcelona EPW file is enough as the base climate file. Local variation is added through UHI, urban morphology, and vegetation layers.

---

## 5. UHI / Heat Comfort Layer

The EPW file gives a **general Barcelona climate profile**, but it does not capture neighborhood-level urban heat differences.

A UHI or heat comfort layer can help adjust the base climate risk according to the selected location.

### Role of UHI Data

```text
User selects location
        ↓
Tool reads base Barcelona EPW climate
        ↓
Tool checks if location falls inside a high / medium / low heat comfort zone
        ↓
Tool adjusts local overheating risk
```

### Example

```text
EPW overheating risk = Medium
Selected neighborhood heat comfort risk = High
Final local heat risk = Medium-High / High
```

### UHI Data Uses

| UHI / Heat Data | Used For |
|---|---|
| Heat comfort zone | Adjust local overheating risk |
| Surface temperature / heat island map | Strengthen environmental evidence |
| Heat vulnerability area | Support health and regenerative framing |
| Population exposed to heat | Optional social vulnerability layer |

### Priority

UHI is **not mandatory** for the first working prototype, but it makes the project stronger because it localizes the climate risk beyond the EPW file.

---

## 6. Urban Morphology Data

Urban morphology data is used to understand the building’s immediate context.

The user selects a location on the map, and the tool clips or queries the urban data around that point, for example within a 50 m or 100 m radius.

### Main Urban Indicators

| Indicator | Dataset Needed | Used For |
|---|---|---|
| Surrounding building height | Building heights / levels | Obstruction, canyon ratio, wind sheltering |
| Building footprint density | Building footprints | Urban density and heat retention proxy |
| Distance to nearby buildings | Building footprints | Solar obstruction and airflow potential |
| Street width | OSM roads or distance between façades | Urban canyon ratio |
| Urban canyon ratio | Height + street width | Wind and solar exposure adjustment |
| Roof exposure | Building geometry + surrounding heights | Green roof potential |
| Vegetation ratio | Green cover / NDVI / parks | Cooling context and ecological layer |

### Height Handling

If exact building heights are not available, use:

```text
estimated_height_m = building_levels × 3 m
```

If neither height nor levels are available, assign a neighborhood average or default value and flag the result as lower confidence.

---

## 7. Passive Strategy Threshold Dataset

This is one of the most important datasets because it contains the logic that turns indicators into design decisions.

It should be a CSV or JSON file that stores passive design thresholds.

### Example Structure

| Strategy | Indicator | Low | Medium | High | Source | Confidence |
|---|---|---:|---:|---:|---|---|
| Exterior shading | WWR | 0.25 | 0.35 | 0.45 | Literature / standard | Medium |
| Exterior shading | Solar exposure risk | 0.30 | 0.60 | 0.80 | Climate analysis | High |
| Cross-ventilation | Room depth | 12 m | 8 m | 6 m | Literature / standard | Medium |
| Night purge | Night temperature drop | 3°C | 5°C | 7°C | Climate analysis | Medium |
| Green roof | Roof exposure | 0.30 | 0.60 | 0.80 | Morphology analysis | Medium |
| Thermal mass | Construction type | Lightweight | Medium | Heavy | Literature / standard | Medium |

### Use

This file feeds the **rule-based scoring engine**.

Example rule:

```text
If façade orientation = west
and WWR > 0.40
and summer solar exposure = high
then exterior shading priority = high
```

---

## 8. RAG Knowledge Base

RAG is used for explanation and justification, not for raw scoring.

The tool should not ask the LLM to guess the passive strategy directly. Instead, the rule engine calculates the score, and the LLM uses RAG to explain the result using relevant studies and standards.

### What Goes Into RAG

| RAG Document Type | Purpose |
|---|---|
| Passive design papers | General evidence for passive strategies |
| Shading studies / guidelines | Explain façade shading recommendations |
| Natural ventilation studies | Explain cross-ventilation conditions |
| Night purge ventilation studies | Explain night cooling potential |
| Thermal mass studies | Explain when thermal mass is useful |
| Green roof cooling studies | Explain roof intervention benefits |
| Adaptive comfort standards | Explain comfort benchmarks and limits |
| Barcelona urban heat studies | Support local climate and UHI relevance |
| Project methodology document | Helps the LLM explain the tool consistently |

### RAG Pipeline

```text
PDFs / papers / standards
        ↓
Text extraction and cleaning
        ↓
Chunking by section or topic
        ↓
Embeddings
        ↓
Vector database
        ↓
Relevant evidence retrieved for each strategy
        ↓
LLM explanation
```

### RAG Output Example

The LLM receives:

```text
Strategy: Exterior shading
Score: 87/100
Precondition: YES
Impact: HIGH
Reason from rule engine: west façade + high WWR + high solar exposure
Retrieved evidence: passive cooling/shading documents
```

Then it writes:

```text
External shading should be prioritized on the west façade because the geometry produces a high solar gain risk. The high WWR increases the impact of direct afternoon radiation, making shading one of the most physically actionable interventions for this design.
```

---

## 9. Rule-Based, RAG, and Optional ML Separation

| System Component | Data Used | Purpose |
|---|---|---|
| Geometry extractor | User model / geometry input | Extract WWR, orientation, roof, openings, room depth |
| Climate processor | EPW file | Extract temperature, wind, humidity, solar indicators |
| UHI processor | Heat comfort / UHI layer | Adjust local heat risk based on selected location |
| Urban morphology processor | OSM, footprints, heights, street width, vegetation | Estimate obstruction, canyon ratio, density, exposure |
| Rule-based engine | Geometry + climate + UHI + morphology + threshold CSV | Decide YES / PARTIAL / NO and HIGH / MEDIUM / LOW |
| RAG | Papers, standards, case studies | Provide evidence and explanation |
| LLM | Rule outputs + retrieved RAG context | Generate architect-readable recommendations |
| Optional decision tree | Synthetic training cases | Predict strategy priority as a lightweight ML experiment |
| Visualization layer | Geometry + strategy scores | Show colored façades, roof interventions, and ventilation arrows |

### Simple Principle

```text
Rules decide.
RAG explains.
LLM communicates.
Decision tree is optional.
```

---

## 10. Full Tool Pipeline

```text
1. User selects location on map
        ↓
2. User uploads or enters simplified building geometry
        ↓
3. Geometry extractor calculates:
      - façade orientation
      - façade area
      - window area
      - WWR
      - roof area
      - plan depth
      - opening configuration
        ↓
4. Climate processor reads Barcelona EPW and calculates:
      - summer temperature risk
      - solar radiation risk
      - wind direction and speed
      - night temperature drop
        ↓
5. UHI processor checks local heat comfort / UHI layer:
      - low / medium / high local heat risk
        ↓
6. Urban morphology processor clips context around selected site:
      - surrounding building heights
      - street width
      - canyon ratio
      - obstruction
      - vegetation ratio
        ↓
7. Indicator builder combines all values:
      - solar risk
      - ventilation potential
      - night cooling potential
      - roof exposure
      - obstruction score
      - local heat risk
        ↓
8. Rule-based scoring engine evaluates passive strategies:
      - exterior shading
      - cross-ventilation
      - night purge ventilation
      - thermal mass
      - green roof
        ↓
9. Optional decision tree predicts best strategy from indicators
        ↓
10. RAG retrieves relevant passive design evidence
        ↓
11. LLM generates explanation and design recommendation
        ↓
12. Tool outputs:
      - ranked scorecard
      - YES / PARTIAL / NO precondition check
      - HIGH / MEDIUM / LOW impact level
      - colored 2D/3D visualization
      - explanation with evidence
```

---

## 11. Strategy Scoring Outputs

Each passive strategy should produce the following structure:

```json
{
  "strategy": "Exterior shading",
  "precondition": "YES",
  "impact": "HIGH",
  "score": 87,
  "target_geometry": "west and south façades",
  "drivers": [
    "high west-facing WWR",
    "high summer solar radiation",
    "medium local UHI risk"
  ],
  "confidence": "medium-high"
}
```

---

## 12. Recommended MVP Dataset Folder Structure

```text
/data
   /raw
      barcelona_weather.epw
      osm_barcelona_buildings.geojson
      osm_barcelona_roads.geojson
      building_heights.geojson
      uhi_heat_comfort_barcelona.geojson
      vegetation_cover.geojson
      sample_user_geometry.json
      /rag_documents
         shading_guidelines.pdf
         natural_ventilation_study.pdf
         night_purge_study.pdf
         thermal_mass_study.pdf
         green_roof_cooling_study.pdf
         adaptive_comfort_standard_notes.pdf

   /processed
      climate_indicators_barcelona.csv
      urban_context_indicators.geojson
      uhi_local_heat_risk.geojson
      passive_strategy_thresholds.csv
      sample_building_indicators.json
      reference_cases.csv
      synthetic_training_cases.csv
```

---

## 13. Minimum Datasets to Gather First

For a 2–3 week prototype, prioritize these:

| Priority | Dataset | Why |
|---|---|---|
| 1 | Barcelona EPW file | Needed for all climate indicators |
| 2 | Sample user building geometry JSON | Needed to test the pipeline |
| 3 | Building footprints / OSM Barcelona | Needed for surrounding context |
| 4 | Building heights or building levels | Needed for obstruction and canyon ratio |
| 5 | Passive strategy thresholds CSV | Needed for rule-based decision logic |
| 6 | UHI / heat comfort layer | Makes local heat risk more specific |
| 7 | Passive design papers | Needed for RAG explanation |
| 8 | Vegetation cover | Useful for green roof and ecological framing |

---

## 14. Final System Logic

The final tool should be described as:

> A location-aware passive design advisor that combines user-provided building geometry, Barcelona EPW climate data, urban morphology, UHI/heat comfort layers, vegetation context, and passive design literature. Structured climate and geometry indicators are evaluated through a rule-based scoring system, while a RAG-supported LLM explains and justifies the recommendations in architect-friendly language.

In simple terms:

```text
User model + location
      ↓
EPW + UHI + morphology + vegetation
      ↓
Rule-based passive strategy scorecard
      ↓
RAG-supported LLM explanation
      ↓
Visualized passive design interventions
```
