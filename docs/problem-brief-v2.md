# Problem Brief v2 — Passive Design Advisor: Barcelona 2025

> Phase-1 loopback artifact. After today's data understanding work, does your
> Session 1 brief still hold? CRISP-DM is iterative — phase 2 routinely sends
> you back to phase 1 to revise the question. That's not failure; that's the
> process working correctly.
>
> Save this file as `docs/problem-brief-v2.md` in your repo. If you revise the
> brief, also update `docs/problem-brief.md` to reflect the new working version.

---

## Was v1 revised? (yes / no)

Yes

## What did the data reveal?

- **Indoor temperature cannot be measured remotely.** The v1 question was built around predicting "indoor thermal discomfort," but there is no open dataset providing indoor temperature readings for Barcelona buildings. The question had to be reframed around physically observable and remotely accessible proxies.
- **EPC data was considered as a proxy but ultimately dropped.** Energy performance certificates are spatially available for Catalonia but measure regulatory compliance, not actual passive design performance. They cannot distinguish whether a good rating comes from passive design or from efficient active systems, making them unsuitable as a ground-truth variable for this tool.
- **The right data exists for a different framing: pre-construction evaluation.** Open datasets for solar radiation (PVGIS), wind and temperature (Open-Meteo), and building morphology (Spanish Cadastre via INSPIRE, OSM Overpass) are all available at sufficient resolution to support a physics-based check of passive design preconditions — but only for a proposed building evaluated against its site context, not for inferring indoor conditions in existing buildings.
- **The tool is a rules engine, not a predictive model.** There is no dataset large enough, nor sufficiently labelled, to train a model that predicts passive design effectiveness from building inputs. The correct architecture is a structured evaluation of physical preconditions per strategy, grounded in established standards (EN 15251, ASHRAE 55), not a learned model.

---

## What changed in the brief

### Decision

- **Was:** An architect or urban environmental analyst evaluating an existing or proposed building in central Barcelona, deciding which passive interventions to pursue. Two decisions supported in sequence: diagnostic (where does passive design fail across typologies?) and prescriptive (which strategies apply to this building?).
- **Now:** A single, prescriptive decision only: an architect evaluating a proposed building during the design phase, before construction, deciding which passive strategies are physically worth implementing given the building's specific geometry and immediate urban context. The diagnostic framing and the "existing building" framing are both dropped.

### User

- **Was:** Architect or urban environmental analyst (two users, loosely defined).
- **Now:** One specific user: an architect working in Barcelona at the design stage of a new building project, who needs a fast first-pass evaluation before committing to passive strategies or resorting to active systems.

### Success criteria

- **Was:** 3 criteria, including one requiring the tool to accept "neighbourhood, building typology, orientation" as inputs and return a ranked list of strategies — inputs that are too coarse to drive physically meaningful recommendations.
- **Now:** 4 criteria. Inputs are now specific geometric parameters (façade orientations, WWR per façade, roof exposure, floor-to-ceiling height, envelope construction type) plus a site location. Each strategy returns a YES / PARTIAL / NO precondition check and a HIGH / MEDIUM / LOW impact rating, each traceable to a specific climate or morphological variable. A 4th criterion requires validation against at least one reference case against EN 15251 or ASHRAE 55.

### Sub-questions

- **Was:** What building sample size is needed for typology rankings? How do we define "passive design failure"? What form does the tool take?
- **Now:** Which climate dataset has sufficient hourly resolution (Open-Meteo vs Meteocat vs EPW)? How do we extract surrounding building heights from the cadastre at usable resolution? Which comfort standard applies to Barcelona (EN 15251 vs ASHRAE 55)? What is the minimum geometric description needed to run all strategy checks without a full 3D model?

### Out of scope

*New additions, given data limits:*

- We are NOT working with existing or already-built buildings (dropped because indoor conditions cannot be measured remotely).
- We are NOT running a full energy simulation (EnergyPlus, DesignBuilder); the tool is a scoping advisor, not a compliance or certification tool.

---

## What we still don't know

- Whether the Spanish Cadastre building height data (derived from number of floors) is accurate enough for shadow obstruction calculations in dense Eixample blocks, or whether OSM or LiDAR-derived heights would be needed.
- At what solar radiation threshold or wind speed threshold each passive strategy tips from LOW to HIGH impact — these weights will need to be defined from literature (ASHRAE, Passivhaus, EN 15251) and are currently unvalidated.
- What the minimum viable geometric input is: whether the tool can run from a simple parameter form (orientation, WWR, floor count, roof area) or whether it genuinely requires a 3D model file as input.

---

## Sign-off

The full revised brief lives in `docs/problem-brief.md` (overwritten if revised).
This file (`problem-brief-v2.md`) is the changelog explaining *why*.

**Team:** Gaelle Habib, Chun-Chun Chang, Nithik Vairamuthu, Vimal TN
**Committed by:** [name]
**Date:** 2025-05-04
