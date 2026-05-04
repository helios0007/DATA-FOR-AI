# Problem Brief — [Passive Design Advisor: Barcelona 2025]


---

## The Environmental Question

Which local climate and urban morphological conditions most strongly determine whether
a proposed building in central Barcelona can meet adaptive thermal
comfort standards through passive design alone, and which passive
strategies are physically actionable given a specific building's
geometry and immediate urban context?

---

## The Design Decision This Supports

An architect is evaluating a proposed building in central Barcelona
during the design phase, before construction, and needs to decide
which passive design interventions — exterior shading, cross-ventilation,
thermal mass, night purge ventilation, green roof — are worth
implementing given the building's specific geometry, orientation,
window-to-wall ratio, and surrounding urban context.

This project gives them a data-grounded scorecard: for each passive
strategy, it checks whether the physical preconditions are met and
estimates the likely impact, so the architect can prioritise
interventions before resorting to active systems.

---

## The Intended User

An architect working in Barcelona at the design stage of a new
building project.

---

## Measurable Success Criteria

1. The tool accepts a 3D model or equivalent geometric inputs
   (façade orientations, areas, window-to-wall ratio per façade,
   roof exposure, floor-to-ceiling height, envelope construction
   type) plus a location in central Barcelona, and returns a
   ranked scorecard of passive strategies.
2. For each strategy, the tool states whether the physical
   precondition is met (YES / PARTIAL / NO) and provides an
   estimated impact level (HIGH / MEDIUM / LOW / NOT APPLICABLE),
   traceable to the specific climate or morphological variable
   that drives the assessment.
3. The analysis pipeline is reproducible from the repo by a
   non-author in under 15 minutes using only open data sources.
4. The tool is validated against at least one reference case
   (a building or design scenario with known passive design
   performance) to confirm that strategy rankings are consistent
   with established standards (EN 15251 or ASHRAE 55).

---

## Risks and Open Questions

**Risks:**

- Wind data at street level in Barcelona may be too coarse to
  meaningfully distinguish exposed vs sheltered sites; station-level
  data may need interpolation or canyon geometry correction.
- Threshold and weight definitions for each strategy (e.g. at what
  solar radiation level does shading become high-impact?) are
  difficult to validate without simulation ground truth; they will
  rely on established standards and literature, which introduces
  uncertainty.
- Urban morphology data from the cadastre may lack sufficient
  height accuracy for shadow obstruction calculations in dense
  blocks.

**Open questions for next session:**

- Which climate dataset provides sufficient hourly resolution for
  Barcelona — Open-Meteo, Meteocat, or EnergyPlus Weather (EPW)
  files?
- How do we extract surrounding building heights and footprints
  from the Barcelona cadastre or urban open data at usable resolution?
- Which comfort standard do we benchmark against — EN 15251
  adaptive model or ASHRAE 55? Are they meaningfully different
  for Barcelona's climate?
- What is the minimum geometric description of a building needed
  to run all strategy checks — can it work without a full 3D model,
  e.g. from a simple parameter form?
---

## Out of Scope

- We are NOT conducting primary data collection (installing sensors,
  running surveys).
- We are NOT working with existing or already-built buildings.
- We are NOT running a full energy simulation (EnergyPlus,
  DesignBuilder, or equivalent); the tool is a scoping advisor,
  not a compliance or certification tool.
- We are NOT building a real-time monitoring dashboard — the tool
  uses open climate and morphological datasets, not live feeds.
- We are NOT covering buildings outside central Barcelona
  neighbourhoods.

---

## Team

| Name | Role on this project |
|---|---|
| [Gaelle Habib] | [tbc] |
| [Chun-Chun Chang] | [tbc] |
| [Nithik Vairamuthu] | [tbc] |
| [Vimal TN] | [tbc] |
