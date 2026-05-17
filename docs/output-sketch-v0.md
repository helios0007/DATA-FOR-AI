# Output Sketch v0 — Passive Design Advisor: Barcelona 2025

> Repo-aligned version regenerated after reviewing the current brief and dataset inventory.
>
> The output is not a graph and not a final simulation report. It is a **first-pass design decision card** that helps an architect decide which passive strategies are physically worth testing further.

---

## What is the final output?

- [x] Web tool / app
- [x] Annotated report-style result card
- [ ] Dashboard
- [ ] Notebook tool
- [ ] Grasshopper component / Rhino plugin
- [ ] API service
- [ ] Other:

**One-sentence description of the output:**

> A web-based Passive Design Advisor that takes a Barcelona site location and simplified building geometry, then returns a ranked strategy card showing which passive design actions are YES / PARTIAL / NO, their estimated impact, the indicators behind the decision, and the data limitations.

---

## Who is the user?

> An architect working on a proposed building in Barcelona during early design stage, before committing to façade, roof, ventilation, or massing strategies.

### What does the user already know?

- The approximate site location.
- The early massing or basic building geometry.
- Façade orientation and approximate WWR.
- Roof area and exposure intention.
- Basic room depth / plan depth assumptions.
- Whether operable openings and thermal mass are being considered.

### What does the user NOT know?

- Whether local climate, wind, solar exposure, and urban morphology make each passive strategy physically suitable.
- Whether a passive strategy is likely to have high, medium, or low impact at this site.
- Which data assumptions or limitations affect the recommendation.
- Whether the strategy should be tested further in a full simulation workflow.

---

## The top 3 actions this output enables

1. Select 2–3 passive strategies worth developing further in the design process.
2. Identify which geometric inputs should be adjusted first, such as WWR, façade shading, plan depth, openings, roof use, or construction type.
3. Decide whether the project needs deeper simulation, revised geometry, or additional site/context data before making design commitments.

---

## Sketch

![Output sketch](./sketches/output-sketch-v0.png)

If the image is not ready yet, use this layout:

- **Top bar:** project location, selected climate file, confidence status, and “not a full simulation” warning.
- **Left panel:** user input summary — location, façade orientation, WWR, roof area, room depth, operable openings, construction type.
- **Centre panel:** ranked passive strategy cards — exterior shading, cross-ventilation, night purge, thermal mass, green roof.
- **Right panel:** evidence and uncertainty — key indicators, thresholds, source datasets, limitations, and RAG-supported explanation.
- **Bottom strip:** next action — “test in full simulation”, “revise geometry”, “collect missing input”, or “proceed with concept”.

---

## Suggested visual hierarchy

### 1. Strategy ranking cards

| Strategy | Precondition | Impact | Confidence | Main reason |
|---|---|---|---|---|
| Exterior shading | YES | HIGH | High | West/south exposure + high summer solar risk + high WWR |
| Cross-ventilation | PARTIAL | MEDIUM | Medium | Wind direction useful, but room depth/openings may limit airflow |
| Night purge | YES | MEDIUM | Medium | Night temperature drop exists, but urban heat may reduce effect |
| Thermal mass | PARTIAL | MEDIUM | Medium | Useful if paired with night cooling, weaker if no ventilation |
| Green roof | YES | LOW–MEDIUM | Medium | Roof exposed; local cooling benefit depends on depth/irrigation/design |

### 2. Indicator explanation block

Each strategy card should show:

- **Input used:** e.g. WWR, orientation, roof area, room depth.
- **Climate indicator:** e.g. overheating hours, night temperature drop, wind direction.
- **Urban indicator:** e.g. canyon ratio, obstruction, local thermal comfort zone.
- **Rule:** e.g. “IF west façade + high solar risk + WWR > threshold → shading priority high.”
- **Confidence:** high / medium / low.
- **Limitation:** one short caveat.

---

## What this output is NOT

- It is not a certified energy simulation or regulatory compliance report.
- It is not a prediction of actual indoor thermal comfort in an existing building.

---

## What would make a user trust this output?

- Every recommendation must expose the evidence chain: **input → indicator → threshold/rule → result → limitation**.

---

## How does this connect to the rest of the work?

| Seminar artifact | How it feeds into this output |
|---|---|
| Problem brief (v2) | Defines the prescriptive design-stage decision and excludes existing-building diagnosis. |
| Datasheets | Provide provenance, coverage, license, and limitations for each adopted dataset. |
| Quality audit | Defines what to trust, what not to trust, and which indicators require caveats. |
| Decision map | Links each user-facing claim to the datasets that support it. |
| System sketch | Shows how data flows from source to rule engine to explanation. |
| Future model card | Explains what the rule engine / optional model does and does not do. |
| Future failure gallery | Shows known bad cases such as missing geometry, outdated UHI layers, or incomplete OSM context. |

---

## Sign-off

**Team:** Gaelle Habib, Chun-Chun Chang, Nithik Vairamuthu, Vimal TN  
**Sketched by:** [name]  
**Last updated:** 2026-05-17
