# Problem Brief v2 — Loopback from Draft02

> Phase-1 loopback artifact for [Group03_problem-brief_draft02.md](Group03_problem-brief_draft02.md).
> After data understanding, we are not changing the project because it failed;
> we are tightening it so the logic matches what the inputs can actually support.

---

## Was v1 revised? (yes / no)

Yes.

## What did the data reveal?

- The project needs to be framed as a structured evaluation framework, not a predictive comfort model. The logic is: read climate inputs, read building geometry, read urban context, then calculate whether each passive strategy is physically plausible and how strong its impact is.
- Climate inputs can come from open meteo datasets and cover the variables needed for decision-making: solar radiation by direction and hour, prevailing wind speed and direction, dry bulb temperature, humidity, and sky conditions.
- Building geometry must come from the 3D model or an equivalent architectural input set. The critical variables are façade orientation and area, window-to-wall ratio, roof exposure, floor-to-ceiling height, thermal mass of the envelope, and existing shading elements.
- Urban context matters because surrounding heights, canyon geometry, open-space distance, and local UHI intensity change whether shading, ventilation, and solar access are actually available at the site.
- The comfort benchmark is not a fixed indoor temperature target. It is the adaptive thermal comfort standard, using EN 15251 or ASHRAE 55 as the comparison point for naturally ventilated buildings in Barcelona’s climate.

## What changed in the brief

### Decision

- **Was:** A generic passive-design advisor with an implied comfort prediction goal.
- **Now:** A calculation-based passive-design evaluation tool that checks whether each strategy is physically actionable and estimates impact from climate, geometry, and urban context.

### User

- **Was:** An architect or analyst deciding what passive interventions to pursue.
- **Now:** An architect in Barcelona at design stage, working from a 3D model or equivalent geometry and needing a ranked scorecard.

### Success criteria

- **Was:** Reproducible analysis and a ranked recommendation.
- **Now:** The tool must accept geometric inputs, run strategy precondition checks, estimate impact levels, and show traceable climate/geometry drivers against an adaptive comfort benchmark.

### Sub-questions

- **Was:** Which outdoor conditions predict indoor discomfort, and which passive strategies close that gap?
- **Now:** What climate inputs matter, what geometric preconditions exist, what urban context modifies them, and what does each strategy score against the comfort benchmark?

### Out of scope

*New additions, given data limits:*

- Direct indoor comfort prediction without indoor measurements.
- Full energy simulation or certification workflows.

## What we still don't know

- Which open meteo source will be the cleanest primary input for Barcelona hourly climate and sky condition variables.
- How much of the geometry can be extracted automatically from the 3D model versus entered manually as a structured form.
- Whether the city morphology layer is detailed enough to quantify shadow obstruction and canyon wind effects consistently.

## Sign-off

The first-version baseline is [Group03_problem-brief_draft02.md](Group03_problem-brief_draft02.md). This file explains why the evaluation logic was tightened.

**Team:** Gaelle Habib, Chun-Chun Chang, Nithik Vairamuthu, Vimal TN
**Committed by:** Team draft
**Date:** 2026-05-04
