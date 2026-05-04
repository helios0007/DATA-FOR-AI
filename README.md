# Session 2 Templates — Data Understanding (CRISP-DM Phase 2)

Drop these into your team repo at the start of Session 2. Before next session every
file should be filled in and committed.

## Where to put them in your repo

```
your-repo/
├── docs/
│   ├── problem-brief.md            (already exists from Session 1)
│   ├── problem-brief-v2.md         (new — the loopback artifact)
│   ├── data-source-inventory.md
│   ├── datasheets/
│   │   ├── <primary-dataset>.md    (copy dataset-datasheet.md, rename)
│   │   └── <secondary-dataset>.md
│   ├── data-quality-audit.md
│   ├── data-to-decision-map.md
│   ├── system-sketch-v0.md
│   └── output-sketch-v0.md
├── notebooks/
│   └── 01-data-profiling.ipynb     (you build this — scaffold in templates/)
└── data/
    └── (small samples only; raw stays gitignored)
```

## The 8 artifacts you owe by 4pm

| # | File | What it is |
|---|---|---|
| 1 | `problem-brief-v2.md` | The phase-1 loopback. What did data reveal? Did your brief change? |
| 2 | `data-source-inventory.md` | Min 5 candidate datasets, scored on the rubric |
| 3 | `datasheets/<primary>.md` | Full datasheet (Gebru et al. 2021) for primary dataset |
| 4 | `datasheets/<secondary>.md` | Full datasheet for secondary dataset (min 2 total) |
| 5 | `01-data-profiling.ipynb` | Runnable profiling notebook for primary dataset |
| 6 | `data-quality-audit.md` | Gaps, anomalies, fitness for the brief |
| 7 | `data-to-decision-map.md` | Sub-questions × data sources × confidence |
| 8 | `system-sketch-v0.md` | Mermaid diagram of how data flows to the user |
| 9 | `output-sketch-v0.md` | One-page sketch of what the user sees at the end |

## The Dataset Assessment Rubric

Use this when scoring datasets in `data-source-inventory.md`. Score 0–2 per axis.
**Adopt only if total ≥ 10/14.**

| Axis | 0 | 1 | 2 |
|---|---|---|---|
| **Provenance** | Source unclear | Source documented | Documented + cited in peer-reviewed work |
| **Resolution match** | Coarser than decision unit | Roughly matches | ≥2× finer than decision unit |
| **Coverage** | Major gaps over our place/time | Minor gaps | Full coverage |
| **License** | Unclear / restrictive | Permissive with attribution | Public domain / CC0 |
| **Access reliability** | Manual scraping, fragile | API but rate-limited or unstable | Stable API or stable bulk download |
| **Bias clarity** | Unknown biases | Some documented | Biases fully documented + quantified |
| **Maintenance** | Stale, no updates | Updated irregularly | Actively maintained, contact available |

## Rules of thumb

- **The 2× rule** — your data resolution should be at least 2× finer than your
  decision unit on every relevant axis (spatial, temporal, spectral).
- **Document the "shouldn't be used for"** — every datasheet must list at least
  2 things this dataset shouldn't be used for. This is the most-skipped section
  and the most useful one.
- **If your license can't be summarized in one sentence, you don't yet
  understand it.** Stop and read.
- **Every artifact in the repo must answer "what is this and why is it here"
  without the author present.**
