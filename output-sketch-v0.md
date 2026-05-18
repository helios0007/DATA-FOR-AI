# Output Sketch v0

> One page. This is what the user sees at the end: a scorecard, not a hidden model output.

---

## What is the final output?

*Choose one form and describe it in one sentence.*

- [x] Dashboard *(interactive web UI with maps / filters / tables)*
- [ ] Annotated map / report *(static, designed to be read)*
- [ ] Notebook tool *(Jupyter notebook with parameter cells, designed to be opened, tweaked, re-run by the user)*
- [ ] Web tool / app
- [ ] Grasshopper component / Rhino plugin
- [ ] API service
- [ ] Other: 

**One-sentence description of the output:**

> An interactive Barcelona passive-design dashboard that accepts climate, geometry, and urban-context inputs, then returns a ranked scorecard of passive strategies with precondition checks, impact estimates, benchmark references, and confidence labels.

---

## Who is the user?

*Be specific. A person with a job title and a moment of use. Not a category ("urban planners") — a person.*

> An architect working on a proposed building in central Barcelona, checking whether shading, cross-ventilation, thermal mass, night purge ventilation, or a green roof is actually worth implementing before construction.

### What does the user already know?

*What's their professional context? What tools do they already use?*

- They know architectural geometry, façade orientation, WWR, and basic passive-design concepts.
- They are likely working from a 3D model or structured design parameters.
- They understand that comfort standards like EN 15251 or ASHRAE 55 matter, even if they do not want to manually compute them.

### What does the user NOT know?

*What's the gap your output fills?*

- Which passive strategies are physically actionable for this specific building.
- Whether a strategy is high, low, or not applicable for the climate and context.
- Which climate or geometry variable is actually driving the recommendation.

---

## The top 3 actions this output enables

*Each action should be concrete: a thing the user does after looking at the output.*

1. Prioritises the passive strategies that are physically feasible and most impactful for the building.
2. Compares two design options side-by-side using the same climate and benchmark logic.
3. Exports a short evidence-backed summary for the team or client.

---

## Sketch

*Embed an image. Hand-drawn on paper, photographed. Figma wireframe. Excalidraw. Screenshot of an analogous existing tool with annotations. Whatever — one image, one page.*

![Output sketch](./sketches/output-sketch-v0.png)

> If you're not ready for an image yet, write a 4-bullet description of the visual layout: what's at the top, the center, the side panel, the bottom.

- Top: building selector, location, and climate summary chips.
- Center: six passive-strategy cards with precondition, impact, and confidence labels.
- Side panel: climate inputs, geometry inputs, and urban context inputs.
- Bottom: adaptive comfort benchmark, source traceability, and limitations.

---

## What this output is NOT

*Two bullets. Protects against scope creep. Be honest.*

- It is not a full energy simulation or certification tool.
- It is not a prediction of actual indoor comfort without indoor measurements.

---

## What would make a user trust this output?

*One bullet. Forces you to think about uncertainty communication early — this gets revisited in Session 7.*

- Every score must show the input that drove it, the benchmark used, and the confidence level.

---

## How does this connect to the rest of the work?

| Seminar artifact | How it feeds into this output |
|---|---|
| Problem brief (v2) | Defines the decision the dashboard supports |
| Datasheets | Shows where each input comes from and what it can and cannot support |
| Quality audit | Makes the climate-input limitations visible to the user |
| Decision map | Tells the dashboard which question each score answers |
| System sketch | Shows how the inputs become the scorecard |
| (Future) Model card | Explains what the logic does, does not do, and where it can fail |
| (Future) Failure gallery | Shows the known edge cases and breakdowns |

---

## Sign-off

**Team:** Gaelle Habib, Chun-Chun Chang, Nithik Vairamuthu, Vimal TN
**Sketched by:** Team draft
**Last updated:** 2026-05-04
