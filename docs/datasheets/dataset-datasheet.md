# Dataset Datasheet — [dataset name]

> One datasheet per adopted dataset. Save as `docs/datasheets/<slug>.md` in
> your repo. Based on Gebru et al. 2021, "Datasheets for Datasets."
>
> The datasheet is a contract: *this is what this data is, this is what it
> can do, this is what it cannot do.* Future-you and your reviewers will
> thank present-you.

---

## 0. Quick reference

- **Dataset name:** 
- **Version / vintage:** 
- **Source URL:** 
- **License:** 
- **Spatial coverage:** 
- **Temporal coverage:** 
- **Native resolution (spatial / temporal):** 
- **Format:** *(GeoTIFF / CSV / NetCDF / Shapefile / API JSON / etc.)*
- **Size:** *(rough — MB / GB)*
- **Datasheet last updated:** [YYYY-MM-DD] by [name]

---

## 1. Motivation

*Why does this dataset exist? Who created it? What was it built for?*

- **Why was the dataset created?**
  
- **Who created the dataset (individuals, organizations)?**
  
- **Who funded the creation of the dataset?**
  
- **For what tasks was the dataset originally intended?**
  

---

## 2. Composition

*What does the dataset contain? At what unit? What's missing?*

- **What does an instance represent?** *(e.g. a satellite scene, a sensor
  reading at a timestamp, a species occurrence record)*
  
- **How many instances are there in total?**
  
- **What features / fields does each instance have?** *(list with data types
  and brief descriptions)*

| Field | Type | Description | Required? |
|---|---|---|---|
|  |  |  |  |
|  |  |  |  |

- **Are there labels or targets associated with each instance?**
  
- **Is any information missing from instances?** *(missing values, gaps —
  where, why, what fraction)*
  
- **Are there relationships between individual instances?** *(temporal,
  spatial, hierarchical)*
  
- **Are there recommended data splits (train/val/test)?**
  

---

## 3. Collection process

*How was the data acquired? By whom? When? Is the sample representative?*

- **How was the data acquired?** *(direct sensor measurement, simulation,
  scraping, citizen science, derived from other data)*
  
- **What instruments / sensors / software were used?**
  
- **Who was involved in the data collection process?** *(researchers, citizen
  scientists, automated systems)*
  
- **Over what time period was the data collected?**
  
- **What was the sampling strategy?** *(probabilistic, deterministic,
  opportunistic, exhaustive)*
  
- **Is the sample representative of the larger population it claims to
  describe?** *(if not, how is it skewed?)*
  
- **Were any ethical review processes conducted?** *(if relevant — IRB,
  consent procedures, etc.)*
  

---

## 4. Preprocessing & cleaning

*What was done to the data before you got it? What did you do?*

- **What preprocessing was done by the dataset creators?** *(calibration,
  atmospheric correction, gridding, interpolation, anonymization)*
  
- **Is the raw data also available?**
  
- **What preprocessing did WE do before adopting the dataset?**
  
- **Where is the preprocessing software / code available?**
  

---

## 5. Uses

*What's this dataset good for? What's it NOT good for?*

- **What tasks has the dataset been used for?**
  
- **Is there a repository linking to papers / systems that use this dataset?**
  
- **What other tasks could this dataset be used for?**
  
- **What tasks should this dataset NOT be used for?** *(at least 2 — be
  specific. e.g. "should not be used to make claims about indoor air quality
  because the sensors are sited outdoors")*
  
  1. 
  2. 

- **Are there any considerations about discrimination, bias, or harm that
  could result from use of this dataset?**
  

---

## 6. Distribution & licensing

- **Under what license is the dataset distributed?**
  
- **Are there any restrictions on use, redistribution, attribution, or
  modification?**
  
- **What's the required attribution string?** *(copy-paste-able)*
  
- **Are there fees for access?**
  
- **Are there export controls or regulatory restrictions?**
  

---

## 7. Maintenance

- **Who supports / hosts / maintains the dataset?**
  
- **How can the maintainer be contacted?** *(email, issue tracker)*
  
- **Is there an erratum?**
  
- **Will the dataset be updated?** *(corrections, new instances, label
  improvements)*
  
- **How often is the dataset updated?**
  
- **Are older versions of the dataset still available?**
  

---

## 8. Limitations relative to OUR project

*The most important section for the seminar. How does this dataset's
character intersect with our problem brief?*

- **Resolution mismatch with our decision unit?**
  
- **Geographic gaps that matter for us?**
  
- **Temporal gaps that matter for us?**
  
- **Biases that could distort our conclusions?**
  
- **What additional sources would compensate for these limits?**
  
- **Verdict for our project:** *(primary / secondary / auxiliary / contextual
  only)*
