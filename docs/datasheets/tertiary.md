# Dataset Datasheet — Open Data BCN Thermal Comfort Zones

> Based on Gebru et al. 2021, "Datasheets for Datasets."

---

## 0. Quick reference

| Field | Value |
|---|---|
| **Dataset name** | Open Data BCN — Thermal Comfort Zones (`confort_termic_od`) |
| **Version / vintage** | Input layers: solar radiation 2011, albedo 2014, vegetation cover 2013 |
| **Source URL** | https://opendata-ajuntament.barcelona.cat/data/en/dataset/confort-termic |
| **License** | Open Data BCN — free download, attribution required; no registration |
| **Spatial coverage** | Full city of Barcelona — 101 km², no spatial gaps |
| **Temporal coverage** | Static snapshot; input layers dated 2011–2014 |
| **Native resolution (spatial / temporal)** | Zone-based polygon layer — 381 polygons, avg ~265,000 m²; no temporal dimension |
| **Format** | GeoPackage (`.gpkg`), EPSG:25831 |
| **Size** | Small (single `.gpkg` file) |
| **Datasheet last updated** | 2026-05-18 by Vimal TN |

---

## 1. Motivation

- **Why was the dataset created?**
  To classify the city of Barcelona into thermal comfort zones as part of the municipal Climate Plan, supporting heat impact assessment and urban planning decisions.

- **Who created the dataset?**
  Ajuntament de Barcelona (Barcelona City Council), published via Open Data BCN.

- **Who funded the creation?**
  Ajuntament de Barcelona / Barcelona Climate Plan.

- **For what tasks was it originally intended?**
  Municipal heat impact studies and urban climate planning. The dataset has been cited in Barcelona heat impact studies.

---

## 2. Composition

- **What does an instance represent?**
  A multipolygon zone covering a contiguous area of the city assigned a single thermal comfort level.

- **How many instances?**
  381 multipolygon features.

- **Key fields:**

| Field | Type | Description | Required? |
|---|---|---|---|
| `geometry` | MultiPolygon | Zone boundary in EPSG:25831 | Yes |
| `gridcode` | Integer (1–6) | Thermal comfort level: 1 = very high comfort (coolest, most shaded, most vegetated) → 6 = very low comfort (highest solar exposure, lowest albedo, least vegetation) | Yes |

- **Are there labels or targets?**
  `gridcode` is the primary label — an ordinal classification derived from the three input layers.

- **Is any information missing?**
  The dataset does not contain the underlying continuous values for solar radiation, albedo, or vegetation cover — only the composite ordinal score. Post-2014 urban changes (superblocks, greening interventions) are not reflected.

- **Relationships between instances?**
  Zones tile the full city with no gaps or overlaps; they are spatially adjacent but otherwise independent.

- **Recommended data splits?**
  Not applicable — used as a spatial lookup table, not for ML training.

---

## 3. Collection process

- **How was the data acquired?**
  Derived dataset: three physical layers were aggregated following the Barcelona Climate Plan methodology:
  1. Incident solar radiation (reference year 2011)
  2. Surface albedo (reference year 2014)
  3. Vegetation cover (reference year 2013)

- **Who was involved?**
  Ajuntament de Barcelona technical staff / Climate Plan team.

- **Over what time period?**
  Input layers span 2011–2014; final dataset published as a single static release.

- **Is the sample representative?**
  Full-city exhaustive coverage — not a sample.

---

## 4. Preprocessing & cleaning

- **What preprocessing was done by the creators?**
  Aggregation of three physical parameter layers into six ordinal comfort classes per the Barcelona Climate Plan methodology.

- **Is the raw data available?**
  Not included in this download; the individual input layers (solar radiation, albedo, vegetation) are not bundled with the GeoPackage.

- **What preprocessing did WE do?**
  None required beyond reprojection check. Used as-is via `gdf[gdf.contains(user_point)]['gridcode']` point-in-polygon lookup.

- **Where is the preprocessing code?**
  Pipeline spatial query utility in the project repo.

---

## 5. Uses

- **What has it been used for?**
  Barcelona heat impact studies; municipal urban climate planning under the Barcelona Climate Plan.

- **What are we using it for?**
  Point-in-polygon spatial lookup: given a user's site coordinates, retrieve the `gridcode` of the containing zone and use it to adjust base EPW overheating risk. Sites in zone 5 or 6 push all cooling strategy scores upward.

- **What other tasks could it be used for?**
  Neighbourhood-level thermal vulnerability screening; broad urban heat mapping overlays; input to urban greening prioritisation.

- **What should it NOT be used for?**
  1. **Building-level or parcel-level thermal assessment** — zones average ~265,000 m²; they cannot distinguish conditions between individual buildings or street canyons.
  2. **Claims about current (post-2014) urban heat conditions** — the input layers predate Barcelona's superblock programme and recent greening interventions; conditions in affected neighbourhoods may differ materially from the mapped values.

- **Discrimination, bias, or harm considerations?**
  None identified for this project's use case.

---

## 6. Distribution & licensing

- **License:** Open Data BCN — permissive open data licence, attribution required.
- **Restrictions:** Attribution required; no registration required for download.
- **Required attribution string:** `Ajuntament de Barcelona — Open Data BCN, confort_termic_od, opendata-ajuntament.barcelona.cat`
- **Fees:** None.
- **Export controls:** None.

---

## 7. Maintenance

- **Who maintains the dataset?**
  Ajuntament de Barcelona / Open Data BCN portal.

- **How to contact?**
  Via the Open Data BCN portal: https://opendata-ajuntament.barcelona.cat/data/en/dataset/confort-termic

- **Will it be updated?**
  No update since original publication. Maintenance rubric score: 0/2 — effectively stale.

- **How often updated?**
  Not updated; input layers are 10–12 years old as of 2026.

- **Are older versions available?**
  Not documented on the portal.

---

## 8. Limitations relative to our project

- **Resolution mismatch with our decision unit?**
  Yes — significant. Our tool assesses individual building sites; the comfort zones average ~265,000 m² (roughly 500 m × 500 m). The `gridcode` provides a neighbourhood-level adjustment, not a site-precise measurement. Use it to shift strategy scores, not as a precise thermal measurement.

- **Geographic gaps that matter for us?**
  None — full Barcelona coverage with no spatial gaps.

- **Temporal gaps that matter for us?**
  Critical. Input data vintages are solar radiation (2011), albedo (2014), vegetation (2013). Post-2014 interventions — Barcelona's superblock programme, park expansions, and rooftop greening — are not reflected. Zones in affected neighbourhoods (e.g., Eixample superblocks) may be systematically pessimistic about current comfort conditions.

- **Biases that could distort our conclusions?**
  Zones that have undergone post-2014 greening may carry a higher (worse) `gridcode` than current conditions warrant, causing the tool to over-recommend cooling interventions for those sites. This bias is conservative (more interventions suggested, not fewer), which is acceptable for a screening tool but should be disclosed.

- **What additional sources would compensate?**
  A recent land surface temperature layer (e.g., Landsat 8/9 or Sentinel-3 LST, 2020–present) would provide a current thermal signal to cross-check against the static `gridcode`. The EPW airport station data (Dataset 1) also partially compensates via the UHI correction pathway.

- **Verdict for our project:**
  **Auxiliary / contextual** — used as a spatial adjustment lookup, not as a primary data source. The 2011–2014 vintage makes it unsuitable as the sole thermal evidence; always pair with the EPW overheating hours calculation (Dataset 1) and flag the data age prominently in the tool UI.
