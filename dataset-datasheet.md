# Dataset Datasheet — Open-Meteo Historical Weather Inputs

> One datasheet per adopted dataset. This one covers the primary climate source used by the Barcelona passive-design scorecard.

---

## 0. Quick reference

- **Dataset name:** Open-Meteo historical weather inputs for Barcelona
- **Version / vintage:** Current API / historical archive access
- **Source URL:** https://open-meteo.com/
- **License:** Public web service with attribution expectations; source-specific underlying data licenses still apply
- **Spatial coverage:** Barcelona and surrounding metropolitan area
- **Temporal coverage:** Historical hourly weather, suitable for design-stage summer analysis
- **Native resolution (spatial / temporal):** Location-based hourly weather values; spatial resolution depends on the underlying source product
- **Format:** API JSON / CSV-like export
- **Size:** Small at request level; large only if bulk historical pulls are saved locally
- **Datasheet last updated:** 2026-05-04 by Team draft

---

## 1. Motivation

*Why does this dataset exist? Who created it? What was it built for?*

- **Why was the dataset created?** To make weather and climate inputs easy to access through a simple API for planning, analysis, and design workflows.
- **Who created the dataset (individuals, organizations)?** Open-Meteo and its contributing weather-data infrastructure.
- **Who funded the creation of the dataset?** Not central to our use case; the service is maintained as a public climate/weather platform.
- **For what tasks was the dataset originally intended?** Weather analysis, climate summaries, planning, and downstream applications that need hourly outdoor conditions.

---

## 2. Composition

*What does the dataset contain? At what unit? What's missing?*

- **What does an instance represent?** A time-stamped weather record for a Barcelona location.
- **How many instances are there in total?** Effectively many hourly records across the selected period.
- **What features / fields does each instance have?**

| Field | Type | Description | Required? |
|---|---|---|---|
| temperature | float | Dry bulb temperature for the hour | Yes |
| relative_humidity | float | Humidity for the hour | Yes |
| wind_speed | float | Hourly wind speed | Yes |
| wind_direction | float | Hourly prevailing wind direction | Yes |
| shortwave_radiation | float | Solar radiation input for façade and roof logic | Yes |
| cloud_cover / sky proxy | float | Proxy for sky conditions and daylighting logic | No / depends on endpoint |

- **Are there labels or targets associated with each instance?** No. The dataset is an input source, not a labeled prediction set.
- **Is any information missing from instances?** Some endpoints may not expose every sky-condition proxy directly, and weather direction becomes less reliable in calm periods.
- **Are there relationships between individual instances?** Yes. The records are temporal and can be aggregated by façade, day, season, or building.
- **Are there recommended data splits (train/val/test)?** Not applicable. This is not a training dataset.

---

## 3. Collection process

*How was the data acquired? By whom? When? Is the sample representative?*

- **How was the data acquired?** Derived from weather/climate sources exposed through the Open-Meteo API.
- **What instruments / sensors / software were used?** Weather station and reanalysis infrastructure behind the API; API retrieval and parsing on our side.
- **Who was involved in the data collection process?** Open-Meteo’s service infrastructure and downstream users.
- **Over what time period was the data collected?** Historical archive plus ongoing access depending on the queried period.
- **What was the sampling strategy?** Deterministic on request: we query the time window and coordinates we need.
- **Is the sample representative of the larger population it claims to describe?** It is representative for the chosen climate location, but it cannot represent street-level microclimates on its own.
- **Were any ethical review processes conducted?** Not applicable for public weather inputs.

---

## 4. Preprocessing & cleaning

*What was done to the data before you got it? What did you do?*

- **What preprocessing was done by the dataset creators?** Weather values are packaged into a usable API layer; some variables may be interpolated or derived from the underlying source product.
- **Is the raw data also available?** The API is the usable interface; raw upstream sources depend on the underlying weather product.
- **What preprocessing did WE do before adopting the dataset?** We normalized timestamps to Barcelona local time, checked for duplicate or shifted hours, and prepared the fields for façade-by-hour logic.
- **Where is the preprocessing software / code available?** In the profiling notebook and analysis scripts that will be built from this repo.

---

## 5. Uses

*What's this dataset good for? What's it NOT good for?*

- **What tasks has the dataset been used for?** Weather analysis, planning, climate summaries, and design-stage environmental checks.
- **Is there a repository linking to papers / systems that use this dataset?** The service is widely used in planning and climate workflows, but our repo will be the main project-specific reference.
- **What other tasks could this dataset be used for?** Passive-design screening, solar exposure estimates, and climate summaries for early-stage building design.
- **What tasks should this dataset NOT be used for?** *(at least 2 — be specific.)*
  1. It should not be used to claim indoor thermal comfort without indoor measurements.
  2. It should not be used to simulate street-canyon wind or shadow at room level by itself.

- **Are there any considerations about discrimination, bias, or harm that could result from use of this dataset?** The main risk is overclaiming precision: if we present gridded or model-based weather as if it were a direct building measurement, the scorecard may sound more certain than it really is.

---

## 6. Distribution & licensing

- **Under what license is the dataset distributed?** Public API access with terms tied to the service and underlying weather sources.
- **Are there any restrictions on use, redistribution, attribution, or modification?** Yes, the service and source product should be cited properly and used according to the endpoint terms.
- **What's the required attribution string?** Open-Meteo climate/weather data, accessed for Barcelona design analysis, with the specific endpoint and access date documented.
- **Are there fees for access?** Not for normal use of the public service.
- **Are there export controls or regulatory restrictions?** None that affect this project in practice.

---

## 7. Maintenance

- **Who supports / hosts / maintains the dataset?** Open-Meteo.
- **How can the maintainer be contacted?** Through the Open-Meteo website and public service documentation.
- **Is there an erratum?** No project-specific erratum noted.
- **Will the dataset be updated?** Yes, the service continues to be maintained.
- **How often is the dataset updated?** Ongoing, depending on the service endpoint and source product.
- **Are older versions of the dataset still available?** Historical archive queries can reproduce past windows if the endpoint supports them.

---

## 8. Limitations relative to OUR project

*The most important section for the seminar. How does this dataset's character intersect with our problem brief?*

- **Resolution mismatch with our decision unit?** Yes, the dataset is climate-scale rather than building-envelope-scale.
- **Geographic gaps that matter for us?** It does not resolve street-level canyon effects or courtyard microclimates.
- **Temporal gaps that matter for us?** Weather series must be aligned carefully to local time and daylight-saving transitions.
- **Biases that could distort our conclusions?** Yes: smoothing of local extremes and overconfidence in model-based weather values are the main risks.
- **What additional sources would compensate for these limits?** Barcelona geometry, cadastre, and morphology layers, plus the adaptive comfort benchmark and validation stations.
- **Verdict for our project:** primary
