# Data → Decision Map

> The bridge from [Group03_problem-brief_draft02.md](Group03_problem-brief_draft02.md) to the data sources and the scorecard logic. Each sub-question maps to the exact input it needs and the confidence we can defend.

---

## The map

| Brief sub-question | Primary data source | Secondary source | Confidence (H/M/L) | Notes |
|---|---|---|---|---|
| What climate inputs matter for the scorecard? | Open-Meteo historical weather inputs | Meteocat / AEMET station observations | H | Hourly temperature, humidity, wind, solar radiation, and sky-condition proxies directly support the calculation framework. |
| What building geometry inputs are needed from the 3D model? | Barcelona cadastre / equivalent 3D geometry layer | Manual structured input form | H | Façade orientation, façade area, WWR, roof area, height, envelope mass, and shading elements are all explicit inputs. |
| What urban context inputs change the recommendation? | Barcelona morphology / city context layer | Open street and open-space data | M | Surrounding heights, canyon geometry, distance to open spaces, and UHI intensity shape shading and ventilation checks, but completeness can vary. |
| What benchmark are we measuring against? | EN 15251 / ASHRAE 55 adaptive thermal comfort standard | Passive-design literature and case studies | H | The project is not predicting comfort; it is checking the calculated conditions against the adaptive comfort benchmark for Barcelona-like climate. |

### Confidence scale

- **HIGH** — adopted dataset(s) directly answer the question at appropriate resolution and coverage. We can defend this in front of a reviewer.
- **MEDIUM** — adopted dataset(s) answer the question with caveats (resolution mismatch, gap, proxy required). Defensible with documentation.
- **LOW** — partial answer only; will require synthesis, modeling assumptions, or proxies. Mark as a known limitation.
- **NONE** — no data backing exists. Either find a new source or revise the brief.

---

## Coverage check

- **Sub-questions with HIGH confidence:**
  - What climate inputs matter for the scorecard?
  - What building geometry inputs are needed from the 3D model?
  - What benchmark are we measuring against?

- **Sub-questions with MEDIUM confidence:**
  - What urban context inputs change the recommendation?

- **Sub-questions with LOW confidence:**
  - None right now, because the logic has been tightened to what the available inputs can support.

- **Sub-questions with NO data backing:**
  - None, provided the project stays within the scorecard logic and does not claim direct indoor comfort prediction.

---

## What this means for the brief

*If any sub-question has NONE or LOW confidence, what's the plan?*

- [ ] Find a new source — list candidates here:
  - A denser urban morphology layer if the current city data cannot resolve canyon geometry well enough.

- [x] Revise the brief — describe the change here, then commit it to `problem-brief-v2.md`:
  - Change the project from indoor prediction to a calculation-based passive-design scorecard.

- [x] Accept LOW confidence as a documented limitation — write the limitation statement here, then add it to `data-quality-audit.md` and to the future model card:
  - Urban context features are medium confidence because canyon geometry and local UHI intensity are not equally complete across all blocks.

---

## Sign-off

**Team:** Gaelle Habib, Chun-Chun Chang, Nithik Vairamuthu, Vimal TN
**Last updated:** 2026-05-04
