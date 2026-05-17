# Data → Decision Map — Passive Design Advisor: Barcelona 2025

> Repo-aligned version regenerated after checking `problem-brief-v2.md`, `data-source-inventory.md`, `data-quality-audit.md`, and `passive_design_advisor_datasets_pipeline.md`.
>
> Core framing: this is a **prescriptive design-stage advisor for proposed buildings**, not a diagnostic tool for existing buildings and not a full energy simulation.

---

## The map

| Brief sub-question | Primary data source | Secondary source | Confidence (H/M/L) | Notes |
|---|---|---|---|---|
| Sub-Q 1: Which climate dataset has sufficient hourly resolution for passive design checks in Barcelona? | Barcelona EPW — TMYx Weather File | Open-Meteo / Meteocat as possible future comparison | HIGH | EPW gives hourly dry bulb temperature, relative humidity, wind speed/direction, and solar radiation variables. Suitable for overheating hours, night temperature drop, wind direction, and solar exposure indicators. Limitation: airport climate may underrepresent dense central Barcelona UHI. |
| Sub-Q 2: How can local urban heat / thermal comfort be adjusted beyond the base EPW climate? | Open Data BCN — Thermal Comfort Zones (`confort_termic_od`) | Vegetation / tree canopy layers; local UHI studies | MEDIUM | Useful as a spatial lookup layer to adjust local heat risk. It is coarser than building scale and based on older input layers, so it should adjust risk, not act as ground truth for indoor comfort. |
| Sub-Q 3: How do we extract surrounding building heights at usable resolution for obstruction, canyon ratio, and shading checks? | ICGC / Barcelona Portal de Dades — MTM Alçades building-volume dataset | OSM building footprints and road network | HIGH | The Alçades GeoPackage gives polygon-level `Z_MIN_VOL` and `Z_MAX_VOL`; height can be derived as `Z_MAX_VOL - Z_MIN_VOL`. It is stronger than relying only on OSM height tags. Requires filtering zero-height artefacts and selecting the right layer/detail level. |
| Sub-Q 4: What immediate urban morphology around the site affects passive strategy feasibility? | OSM Buildings + Roads via Overpass / Geofabrik | ICGC Alçades; cadastral or street-width proxy | MEDIUM | OSM provides footprints and street network geometry; height tags may be incomplete, but heights can be supplemented by Alçades. Street width may need to be inferred from road classes or façade distances, so confidence is medium. |
| Sub-Q 5: What minimum geometric input is needed from the architect to run strategy checks without a full 3D model? | User building geometry dataset: manual form / JSON / Rhino-Revit export | Future IFC / Speckle / Grasshopper pipeline | MEDIUM | Required fields: location, façade orientation, WWR by façade, building height/massing, roof area/exposure, room depth/plan depth, operable openings, and construction type. Confidence is medium because the exact minimum input may change after testing. |
| Sub-Q 6: Which passive strategies are physically worth implementing for the selected building and site? | Passive strategy threshold dataset (`strategy_thresholds.csv` or `.json`) | EN 15251, ASHRAE 55, Passivhaus/design guidance, RAG knowledge base | MEDIUM | The rule engine can return YES / PARTIAL / NO and HIGH / MEDIUM / LOW impact based on indicators. Current thresholds are defensible as documented assumptions, but should be validated with reference cases. |
| Sub-Q 7: How should the user understand why a recommendation was made? | RAG knowledge base: passive design papers, standards, and design manuals | Final rule-engine outputs and indicator table | MEDIUM | RAG is used for explanation and justification only. It should not make the raw decision. The LLM translates rule-engine results into readable explanation with caveats and evidence links. |
| Sub-Q 8: How can the output be trusted by an architect? | Data-quality audit + datasheets + confidence labels | Reference cases / failure gallery / model card | MEDIUM | Trust comes from showing source, indicator value, rule threshold, confidence, and limitation. Full trust requires reference-case validation, which is still an open seam. |

---

## Coverage check

### Sub-questions with HIGH confidence

- Sub-Q 1: Hourly climate baseline from EPW.
- Sub-Q 3: Surrounding building height extraction from ICGC / Alçades dataset.

### Sub-questions with MEDIUM confidence

- Sub-Q 2: Local heat comfort adjustment.
- Sub-Q 4: Urban morphology and street-context indicators.
- Sub-Q 5: Minimum viable geometry input.
- Sub-Q 6: Passive strategy scoring.
- Sub-Q 7: RAG-supported explanation.
- Sub-Q 8: Trust and uncertainty communication.

### Sub-questions with LOW confidence

- None as core MVP questions, provided the system remains a first-pass advisor rather than a validated simulator.

### Sub-questions with NO data backing

- Predicting real indoor thermal comfort for existing buildings.
- Ranking existing buildings city-wide by passive design failure.
- Proving actual post-construction energy saving or health impact.

These are intentionally out of scope based on `problem-brief-v2.md`.

---

## What this means for the brief

- [x] Find a new source — list candidates here:
  - For validation: reference case studies from EN 15251 / ASHRAE 55 / passive design literature.
  - For urban heat improvement: newer UHI / land surface temperature / municipal climate layers if available.
  - For geometry automation: IFC / Speckle / Rhino / Revit export tests.

- [x] Revise the brief — describe the change here, then commit it to `problem-brief-v2.md`:
  - The brief has already shifted from predicting existing-building indoor discomfort to evaluating proposed-building passive strategy feasibility.
  - The tool should remain prescriptive and design-stage focused.

- [x] Accept MEDIUM confidence as a documented limitation — write the limitation statement here, then add it to `data-quality-audit.md` and to the future model card:
  - The system provides early-stage passive strategy prioritisation. It does not replace EnergyPlus, DesignBuilder, compliance modelling, or measured indoor monitoring. Its confidence depends on the quality of geometric input, the vintage of urban heat datasets, and the documented assumptions inside the passive strategy thresholds.

---

## Sign-off

**Team:** Gaelle Habib, Chun-Chun Chang, Nithik Vairamuthu, Vimal TN  
**Last updated:** 2026-05-17
