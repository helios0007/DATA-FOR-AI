# Data Quality Audit — [primary dataset name]

> Honest assessment of the dataset's fitness for YOUR brief, based on what
> profiling revealed. Not a generic data-quality report — specifically
> answers "can we use this for what we're trying to do?"
>
> Save as `docs/data-quality-audit.md` in your repo.

---

## Dataset under audit

- **Dataset:** 
- **Profiling notebook:** `notebooks/01-data-profiling.ipynb`
- **Audit performed by:** [name(s)]
- **Date:** [YYYY-MM-DD]

---

## Gaps

### Temporal gaps

*Date ranges where data is missing, sparse, or unreliable. Be specific —
"there's a gap from 2020-03 to 2020-06" not "some data is missing."*

- 

### Spatial gaps

*Locations or regions where coverage is missing, sparse, or unreliable.*

- 

### Field-level gaps

*Which columns / variables are unreliable? What fraction is missing? Are
the missing values random or structured?*

| Field | % missing | Pattern of missingness | Implication |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |

---

## Anomalies found during profiling

*List each anomaly discovered, with a one-sentence diagnosis. Include
suspicious values (e.g. negative PM2.5 readings, dates in 2099, sensor IDs
of zero).*

| # | Anomaly | Diagnosis | Action taken |
|---|---|---|---|
| 1 |  |  |  |
| 2 |  |  |  |
| 3 |  |  |  |
| 4 |  |  |  |
| 5 |  |  |  |

---

## Bias check

*From the bias taxonomy in the lecture: selection / measurement / coverage /
temporal drift / label bias. Which apply to this dataset?*

- **Selection bias:** 
- **Measurement bias:** 
- **Coverage bias:** 
- **Temporal drift / non-stationarity:** 
- **Label bias** *(if applicable):* 

---

## Fitness for OUR brief

*For each sub-question of your problem brief, can this dataset answer it?*

- **Sub-question 1:** [paste sub-question]
  - **Answer:** Yes / Partial / No
  - **Why:** 

- **Sub-question 2:** [paste sub-question]
  - **Answer:** Yes / Partial / No
  - **Why:** 

- **Sub-question 3:** [paste sub-question]
  - **Answer:** Yes / Partial / No
  - **Why:** 

---

## Decisions

- **What we WILL use this dataset for:**
  
- **What we will NOT use this dataset for:** *(at least 2 specific things)*
  1. 
  2. 

- **What additional source(s) we'd need to fill the gaps:**
  

---

## Implications for the brief

*Does this audit force a change to the problem brief? If yes, document the
change in `problem-brief-v2.md` and link from here.*

- 

---

## Per-team-member contributions

*Each team member must write at least one paragraph in this file. Use this
section.*

### [Name]

### [Name]

### [Name]

### [Name]
