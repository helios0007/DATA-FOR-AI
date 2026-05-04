# Data → Decision Map

> The bridge from your problem brief to your data inventory. For each
> sub-question in the brief, which dataset answers it, and at what
> confidence?
>
> If any sub-question has NO data backing it, you have two choices:
> 1. Find a new source.
> 2. Revise the brief (`problem-brief-v2.md`).
>
> There is no third option called "we'll figure it out later."
>
> Save as `docs/data-to-decision-map.md` in your repo.

---

## The map

| Brief sub-question | Primary data source | Secondary source | Confidence (H/M/L) | Notes |
|---|---|---|---|---|
| Sub-Q 1: [paste] | | | | |
| Sub-Q 2: [paste] | | | | |
| Sub-Q 3: [paste] | | | | |
| Sub-Q 4: [paste] | | | | |

### Confidence scale

- **HIGH** — adopted dataset(s) directly answer the question at appropriate
  resolution and coverage. We can defend this in front of a reviewer.
- **MEDIUM** — adopted dataset(s) answer the question with caveats
  (resolution mismatch, gap, proxy required). Defensible with documentation.
- **LOW** — partial answer only; will require synthesis, modeling
  assumptions, or proxies. Mark as a known limitation.
- **NONE** — no data backing exists. Either find a new source or revise
  the brief.

---

## Coverage check

- **Sub-questions with HIGH confidence:**
  - 

- **Sub-questions with MEDIUM confidence:**
  - 

- **Sub-questions with LOW confidence:**
  - 

- **Sub-questions with NO data backing:**
  - 

---

## What this means for the brief

*If any sub-question has NONE or LOW confidence, what's the plan?*

- [ ] Find a new source — list candidates here:
  - 

- [ ] Revise the brief — describe the change here, then commit it to
      `problem-brief-v2.md`:
  - 

- [ ] Accept LOW confidence as a documented limitation — write the
      limitation statement here, then add it to `data-quality-audit.md`
      and to the future model card:
  - 

---

## Sign-off

**Team:** [names]
**Last updated:** [YYYY-MM-DD]
