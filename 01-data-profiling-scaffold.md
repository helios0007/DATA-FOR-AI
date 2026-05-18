# Profiling Notebook — Scaffold

> This scaffold maps the cells you need in `notebooks/01-data-profiling.ipynb`.
> Copy each cell into a new Jupyter notebook in your repo. Adapt the
> dataset-loading cell to your data source.
>
> Your final notebook must be runnable end-to-end from a clean kernel.

---

## Cell 1 — Markdown: title & purpose

```markdown
# Data Profiling — Open-Meteo Historical Weather Inputs (Barcelona)

**Purpose:** describe the climate dataset's shape, distributions, gaps, and anomalies
so we know what we have before building the Barcelona passive-design scorecard.

**Input:** Barcelona hourly weather export from Open-Meteo or the local CSV cache of API pulls.
**Output:** a list of findings written into `docs/data-quality-audit.md`.
```

## Cell 2 — Imports

```python
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

pd.set_option("display.max_columns", 50)
pd.set_option("display.max_rows", 100)
```

## Cell 3 — Load the data

> Adapt this cell. CSV is the default; for GeoTIFF use `rioxarray`, for
> NetCDF use `xarray`, for shapefiles use `geopandas`.

```python
df = pd.read_csv("../data/open-meteo-barcelona.csv")
df.head()
```

## Cell 4 — Shape & dtypes

```python
print(f"Rows: {df.shape[0]:,}")
print(f"Columns: {df.shape[1]}")
print()
print(df.dtypes)
```

## Cell 5 — Missing values

```python
missing = df.isna().mean().sort_values(ascending=False)
missing[missing > 0]
```

## Cell 6 — Numeric summary

```python
df.describe()
```

## Cell 7 — Categorical / ID summary

```python
cat_cols = df.select_dtypes(include="object").columns
for col in cat_cols:
    n_unique = df[col].nunique()
    print(f"{col}: {n_unique:,} unique values")
    if n_unique < 20:
        print(df[col].value_counts())
    print()
```

## Cell 8 — Temporal coverage

> Adapt to the actual timestamp column if the export uses a different name.

```python
df["timestamp"] = pd.to_datetime(df["timestamp"])
print(f"Date range: {df['timestamp'].min()} → {df['timestamp'].max()}")
print(f"Total span: {(df['timestamp'].max() - df['timestamp'].min()).days} days")
print(f"Unique dates: {df['timestamp'].dt.date.nunique():,}")
```

## Cell 9 — Detect temporal gaps

```python
daily_counts = df.groupby(df["timestamp"].dt.date).size()
expected_days = pd.date_range(daily_counts.index.min(), daily_counts.index.max())
missing_days = set(expected_days.date) - set(daily_counts.index)
print(f"Missing days: {len(missing_days)}")
if missing_days:
    print(sorted(missing_days)[:10], "...")
```

## Cell 10 — Spatial coverage *(if dataset has lat/lon)*

```python
if {"lat", "lon"}.issubset(df.columns):
    print(f"Lat range: {df['lat'].min():.4f} → {df['lat'].max():.4f}")
    print(f"Lon range: {df['lon'].min():.4f} → {df['lon'].max():.4f}")
    print(f"Unique locations: {df[['lat', 'lon']].drop_duplicates().shape[0]:,}")
else:
    print("No lat/lon columns in this export; spatial coverage is represented by the query location.")
```

## Cell 11 — Visualization 1: distribution of one key variable

```python
fig, ax = plt.subplots(figsize=(10, 5))
sns.histplot(df["temperature"], bins=50, ax=ax)
ax.set_title("Distribution of hourly dry-bulb temperature")
plt.tight_layout()
plt.show()
```

## Cell 12 — Visualization 2: time series or spatial map of coverage

```python
fig, ax = plt.subplots(figsize=(12, 4))
daily_counts.plot(ax=ax)
ax.set_title("Records per day — coverage over time")
ax.set_ylabel("count")
plt.tight_layout()
plt.show()
```

## Cell 13 — Markdown: anomaly hunt

```markdown
## Anomalies found

Look at the cells above and list every weird thing. Examples:
- Suspicious constant values
- Negative values where they shouldn't exist (e.g. negative PM2.5)
- Dates outside the expected range (1970? 2099?)
- Duplicate records
- Sensor IDs of zero or empty strings
- Sudden cliffs or zeroes in time series
- Outliers > 5σ from the mean
```

## Cell 14 — Markdown: 3 things profiling revealed I didn't know

```markdown
## What did profiling reveal that we didn't know?

1. Hourly temperature, humidity, wind, and solar inputs are available at the right cadence for the scorecard.
2. Timestamp normalization is necessary because the same data behaves differently in UTC versus Barcelona local time.
3. The dataset is useful for climate screening, but not enough on its own for street-level microclimate claims.

**Implications for the brief:** This confirms the brief should stay framed as a calculation-based passive-design scorecard rather than an indoor comfort prediction. The climate layer supports the scoring logic, but the geometry and urban-context layers are still required for strategy checks.

**Implications for the pipeline (Session 3):** We need timezone correction, column harmonization, and a clean join between weather records and building geometry before any strategy scoring can run. We also need to keep a simple data dictionary so the team uses the same column names in the notebook and the audit.
```

## Cell 15 — Save profile summary

> Optional but recommended — saves a machine-readable profile alongside the
> notebook so it's diffable in git.

```python
profile_summary = {
    "dataset": "Open-Meteo Historical Weather Inputs (Barcelona)",
    "rows": int(df.shape[0]),
    "cols": int(df.shape[1]),
    "missing_pct": missing.to_dict(),
    "numeric_summary": df.describe().to_dict(),
    "date_range": [str(df["timestamp"].min()), str(df["timestamp"].max())],
    "missing_days": len(missing_days),
}

import json
with open("../data/profile-summary.json", "w") as f:
    json.dump(profile_summary, f, indent=2, default=str)
print("Saved profile-summary.json")
```

---

## Reproducibility check

Before committing:

1. Restart kernel.
2. Run all cells.
3. Confirm no errors.
4. Confirm at least 2 visualizations rendered.
5. Confirm the "what did profiling reveal" cell has 3 specific findings.
6. Commit notebook + `profile-summary.json` (small) to repo.
   Do NOT commit raw data unless it's small (<5 MB) and licensed for
   redistribution.
