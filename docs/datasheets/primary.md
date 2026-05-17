# Dataset Datasheet — Barcelona TMYx EPW Weather File

> Save as `docs/datasheets/epw-barcelona-tmyx.md` in your repo.
> Based on Gebru et al. 2021, "Datasheets for Datasets."
>
> The datasheet is a contract: *this is what this data is, this is what it
> can do, this is what it cannot do.* Future-you and your reviewers will
> thank present-you.

---

## 0. Quick reference

- **Dataset name:** Barcelona El Prat Airport — TMYx Typical Meteorological Year
- **Version / vintage:** TMYx; period of record 1973–2023; typical months drawn from years 1987–2020
- **Source URL:** https://www.ladybug.tools/epwmap/ (mirror of https://climate.onebuilding.org)
- **License:** Free for research and commercial use; attribution required (see section 6)
- **Spatial coverage:** Single point — WMO station 081810, Barcelona El Prat Airport; lat 41.2928°N, lon 2.0700°E, elevation 5 m a.s.l.
- **Temporal coverage:** One synthetic TMY year (8,760 hours); each month drawn from a different representative source year: Jan=1999, Feb=1989, Mar=2011, Apr=2009, May=2016, Jun=1996, Jul=2014, Aug=2008, Sep=2009, Oct=1999, Nov=1987, Dec=2020
- **Native resolution (spatial / temporal):** Point station / 1 hour
- **Format:** EPW (EnergyPlus Weather) — plain-text CSV with 8-line metadata header; 35 fields per data row
- **Size:** 1.53 MB
- **Datasheet last updated:** 2025-05-17 by Passive Design Advisor team

---

## 1. Motivation

- **Why was the dataset created?** To provide a freely accessible, standardised typical-year climate file for building energy simulation and passive design analysis at the Barcelona airport weather station. TMYx was developed to replace older TMY2/TMY3 formats using more recent observed data and a globally consistent methodology (ISO 15927-4:2005).

- **Who created the dataset (individuals, organizations)?** Linda K. Lawrie and Drury B. Crawley (volunteer effort), distributed via climate.onebuilding.org. Solar radiation variables computed from ERA5 reanalysis data (ECMWF / Oikolab). Raw observations sourced from NOAA's NCEI Integrated Surface Database (ISD). Airport observations originally collected by AEMET (Agencia Estatal de Meteorología, Spain).

- **Who funded the creation of the dataset?** Volunteer effort by Lawrie & Crawley with no dedicated funding. Underlying ISD maintained by NOAA/NCEI (US federal). ERA5 reanalysis maintained by ECMWF under Copernicus Climate Change Service funding.

- **For what tasks was the dataset originally intended?** Building energy simulation (EnergyPlus, DOE-2, ESP-r), passive design screening, climate-based daylighting modelling (Radiance, Daysim), HVAC sizing, outdoor thermal comfort analysis, and solar yield estimation.

---

## 2. Composition

- **What does an instance represent?** One hour of the synthetic typical meteorological year — a single row containing atmospheric and radiation conditions at Barcelona El Prat Airport for that hour of the year.

- **How many instances are there in total?** 8,760 rows (365 days × 24 hours; non-leap year).

- **What features / fields does each instance have?**

| Field | Type | Description | Required for our project? |
|---|---|---|---|
| Year | int | Source year from which this hour was drawn | Traceability only |
| Month | int | Month (1–12) | Yes |
| Day | int | Day of month (1–31) | Yes |
| Hour | int | Hour of day (1–24) | Yes |
| Dry Bulb Temperature | float (°C) | Outdoor air temperature | **Yes** — comfort checks, diurnal swing |
| Dew Point Temperature | float (°C) | Moisture content indicator | Yes — humidity comfort |
| Relative Humidity | float (%) | Outdoor relative humidity | Yes — ventilation comfort |
| Atmospheric Pressure | float (Pa) | Station-level barometric pressure | No |
| Global Horizontal Irradiance (GHI) | float (Wh/m²) | Total solar radiation on horizontal surface | **Yes** — shading strategy |
| Direct Normal Irradiance (DNI) | float (Wh/m²) | Direct beam solar radiation | **Yes** — façade solar load calculation |
| Diffuse Horizontal Irradiance (DHI) | float (Wh/m²) | Scattered solar radiation | Yes — daylighting and indirect solar gain |
| Wind Direction | float (°) | 0–360°, meteorological convention | **Yes** — cross-ventilation orientation check |
| Wind Speed | float (m/s) | Speed at 10 m reference height | **Yes** — cross-ventilation and night purge checks |
| Total Sky Cover | int (oktas 0–10) | Total cloud cover fraction | Auxiliary |
| Opaque Sky Cover | int (oktas 0–10) | Opaque cloud fraction | Auxiliary |
| Visibility | float (km) | Atmospheric visibility | No |
| Ceiling Height | float (m) | Cloud base height | No |
| Present Weather | coded string | WMO present weather observation codes | No |
| Precipitable Water | float (mm) | Atmospheric water vapour column | No |
| Aerosol Optical Depth | float | Atmospheric turbidity proxy | No |
| Snow Depth | float (cm) | Ground snow depth | No |
| Albedo | float | Surface reflectance (often placeholder) | No |
| Liquid Precipitation Depth | float (mm) | Hourly rainfall | No |

- **Are there labels or targets associated with each instance?** No — this is observational climate data, not a labelled ML dataset.

- **Is any information missing from instances?** Zero missing values in primary fields (dry bulb temperature, GHI, wind speed) — confirmed by parsing. Some auxiliary fields (aerosol optical depth, albedo) carry placeholder values (999 / 9999) for hours without reliable observations; these fields are not used in our pipeline.

- **Are there relationships between individual instances?** Yes — strong temporal autocorrelation between consecutive hours. The TMY construction algorithm selects whole calendar months from different source years, creating 11 synthetic seams per year (at month boundaries) where small discontinuities in the time series may occur.

- **Are there recommended data splits (train/val/test)?** Not applicable — this is a deterministic climate input, not a machine learning dataset.

---

## 3. Collection process

- **How was the data acquired?** Raw hourly observations collected by automated and manual instruments at Barcelona El Prat Airport, reported to NOAA NCEI's Integrated Surface Database. Solar radiation variables (GHI, DNI, DHI) are not directly measured at this station; they are calculated from ERA5 satellite-derived reanalysis data for the 2004–2018 period, and from cloud cover and atmospheric variables using the Perez decomposition model for earlier periods.

- **What instruments / sensors / software were used?** WMO-standard meteorological instruments at the airport (thermometer, hygrometer, cup anemometer, barometer). Solar variables computed via ERA5 reanalysis (ECMWF numerical weather model) and processed with White Box Technologies EPW conversion software.

- **Who was involved in the data collection process?** AEMET staff for airport observations; NOAA NCEI for ISD archiving and quality control; ECMWF for ERA5 production; Lawrie & Crawley for TMYx month selection and EPW formatting.

- **Over what time period was the data collected?** Period of record 1973–2023 (51 years of source observations). The TMY months are drawn from 1987–2020.

- **What was the sampling strategy?** Deterministic — the TMY algorithm (ISO 15927-4:2005) selects the calendar month from the historical record whose cumulative distribution functions of key variables (dry bulb temperature, GHI, wind speed) most closely match the long-term climatological average for that month. It is not random sampling.

- **Is the sample representative of the larger population it claims to describe?** It represents a *typical* year — the central tendency of historical climate — not an extreme or recent year. By construction it under-represents heatwave events (which are tails of the distribution) and does not capture accelerating recent warming trends. It also represents the airport location, not the urban interior — see section 8.

- **Were any ethical review processes conducted?** Not applicable.

---

## 4. Preprocessing & cleaning

- **What preprocessing was done by the dataset creators?**
  - NOAA NCEI: quality control flagging, gap-filling, conversion to hourly time steps from sub-hourly or 3-hourly synoptic observations
  - Lawrie & Crawley: ISD-to-EPW format conversion, local time adjustment (UTC+1 for Barcelona), solar radiation calculation using ERA5 and Perez model, TMY month selection (ISO 15927-4:2005), insertion of ASHRAE design conditions and ground temperature profiles in the 8-line EPW header
  - Extensive out-of-range value checking and correction documented by climate.onebuilding.org

- **Is the raw data also available?** Yes — NOAA NCEI ISD data freely available at https://www.ncei.noaa.gov/products/land-based-station/integrated-surface-database. ERA5 reanalysis available from ECMWF via the Copernicus Climate Data Store (cds.climate.copernicus.eu).

- **What preprocessing did WE do before adopting the dataset?**
  - Parsed the full EPW file in Python to extract hourly arrays for all fields used in the pipeline
  - Computed monthly summary statistics: mean, max, min, 95th percentile for dry bulb temperature, GHI, wind speed
  - Computed average daily diurnal temperature swing per month (daily max − min, averaged across all days in month)
  - Computed summer cooling degree hours above 26°C threshold
  - Confirmed 0 missing values in all primary fields
  - Key statistics confirmed from file: summer (JJA) mean dry bulb 23.7°C, peak 31.4°C; winter (DJF) mean 10.3°C, min 3.0°C; July average diurnal swing 6.5°C

- **Where is the preprocessing software / code available?** scripts\parse_epw.py for parsing, and outputs\epw_summary.json for parsing output.

---

## 5. Uses

- **What tasks has the dataset been used for?** Building energy simulation (EnergyPlus, DesignBuilder, OpenStudio), passive design analysis (Ladybug/Honeybee in Grasshopper), climate-based daylighting modelling (Radiance, DIVA), HVAC sizing, solar PV yield estimation, outdoor thermal comfort analysis (UTCI, PET), and wind rose analysis.

- **Is there a repository linking to papers / systems that use this dataset?** climate.onebuilding.org documents all derivative tools and publications. The Ladybug Tools community forum (discourse.ladybug.tools) contains extensive applied examples.

- **What other tasks could this dataset be used for?**
  - Computing the running mean outdoor temperature required by EN 16798-1 / ASHRAE 55 adaptive comfort models
  - Generating sun path diagrams and solar angle inputs for shading geometry calculations (pvlib)
  - Estimating natural ventilation availability hours (hours where wind speed > threshold and temperature < comfort limit)
  - Estimating night purge potential (hours where outdoor temp < indoor temp − 2°C after sunset)

- **What tasks should this dataset NOT be used for?**
  1. **Should not be used to assess extreme heat event risk or heatwave frequency** — the TMY algorithm explicitly selects *typical* months, so heatwave weeks (e.g. summer 2003, 2019, 2022 in Barcelona) are systematically excluded. Strategy impact estimates derived from the EPW will be non-conservative for buildings exposed to heat extremes.
  2. **Should not be used to represent urban microclimates in central Barcelona without correction** — the station is at El Prat Airport, ~12 km from the Eixample, in a relatively open peri-urban location. Nighttime temperatures in dense central neighbourhoods are consistently 1–2°C warmer due to urban heat island effects, and wind speeds at street level in deep canyons are 30–60% lower than the 10 m airport anemometer reading.
  3. **Should not be used as a real historical time series** — TMY months are drawn from different source years; the file does not represent any single real year and cannot be used for trend analysis, event attribution, or chronological comparison with measured data.

- **Are there any considerations about discrimination, bias, or harm that could result from use of this dataset?** The airport-vs-urban bias (point 2 above) could cause the tool to underestimate overheating risk in dense, low-SVF neighbourhoods, potentially leading to under-specification of passive cooling measures. This is a systematic conservative bias that affects all strategy scores in the same direction. It is partially mitigated by pairing the EPW with the Thermal Comfort Zones layer (dataset 4 in inventory) and should be disclosed to tool users.

---

## 6. Distribution & licensing

- **Under what license is the dataset distributed?** Free for all uses (research and commercial) with attribution. No formal open-source license designation, but treated as open data by the global building simulation community.

- **Are there any restrictions on use, redistribution, attribution, or modification?** No restrictions on use or redistribution. Attribution is required. Modified or derived versions should be clearly identified as derivatives.

- **What's the required attribution string** (copy-paste-able):
  ```
  Lawrie, Linda K., Drury B. Crawley. 2022. Development of Global Typical
  Meteorological Years (TMYx). https://climate.onebuilding.org.
  Station: Barcelona El Prat Airport, WMO 081810.
  Source observations: NOAA NCEI Integrated Surface Database.
  Solar data: ERA5 reanalysis, ECMWF / Oikolab.
  ```

- **Are there fees for access?** No — free download, no registration required.

- **Are there export controls or regulatory restrictions?** None.

---

## 7. Maintenance

- **Who supports / hosts / maintains the dataset?** Linda K. Lawrie and Drury B. Crawley (volunteer); hosted at climate.onebuilding.org and mirrored by Ladybug Tools at ladybug.tools/epwmap/.

- **How can the maintainer be contacted?** Via the contact page at climate.onebuilding.org or the Ladybug Tools community forum at discourse.ladybug.tools.

- **Is there an erratum?** None known for this station.

- **Will the dataset be updated?** Yes — newer TMYx releases are published periodically, extending the period of record. The 2026 release on climate.onebuilding.org covers data through 2025 with updated ERA5 solar inputs.

- **How often is the dataset updated?** Irregularly — approximately every 1–2 years for major new releases.

- **Are older versions of the dataset still available?** Yes — climate.onebuilding.org maintains prior releases. The period of record is encoded in the file name (e.g. `TMYx.2004-2018`) and in the COMMENTS row of the EPW header.

---

## 8. Limitations relative to OUR project

- **Resolution mismatch with our decision unit?**
  Temporal resolution is excellent — 1-hour intervals are finer than any seasonal or monthly decision unit in our rule engine. Spatial resolution is the fundamental problem: a single airport point cannot represent intra-city microclimate variation. The Eixample, Gràcia, El Born, and Sant Martí all have meaningfully different thermal conditions driven by urban morphology, surface albedo, vegetation cover, and proximity to the sea.

- **Geographic gaps that matter for us?**
  The airport is ~12 km southwest of central Barcelona in a relatively open, low-density peri-urban location. It systematically misrepresents dense central neighbourhoods in three ways: (1) nighttime temperatures are 1–2°C cooler than the urban core due to lower urban heat island intensity at the airport; (2) daytime wind speeds are higher than street-level values in deep street canyons (H/W ratio > 1); and (3) urban surface albedo is lower in the city centre, increasing solar absorption beyond what the EPW solar data implies for an airport setting.

- **Temporal gaps that matter for us?**
  The TMY base period ends in 2023 but the typical months are assembled from 1987–2020. It does not capture the accelerated warming of the most recent years. For a tool guiding design decisions for buildings with 50+ year lifespans, the EPW underestimates future cooling demand. This is a known limitation of all TMY-based tools and should be disclosed to users.

- **Biases that could distort our conclusions?**
  The most operationally significant bias: the airport-vs-urban-core temperature gap causes our tool to **underestimate** overheating risk and therefore **underestimate** the impact scores of all passive cooling strategies. This is a conservative bias in the wrong direction for a tool intended to promote passive interventions.

  A second important bias: the July average diurnal swing from the EPW is only **6.5°C** — below the 10°C threshold commonly cited in passive cooling literature as the point above which night purge ventilation and thermal mass become highly effective. As a result, our rule engine will rate night purge as MEDIUM rather than HIGH impact for most Barcelona sites. This is climatologically accurate for the airport but may underestimate performance in urban areas where radiative cooling at night is further reduced, compressing the swing even further — reinforcing rather than reversing the rating.

- **What additional sources would compensate for these limits?**
  - Dataset 4 (`confort_termic_od.gpkg`, Thermal Comfort Zones) provides a neighbourhood-level zone lookup that partially corrects for the UHI gap
  - Meteocat (Servei Meteorològic de Catalunya) urban stations could provide validation temperature data for a central Barcelona neighbourhood
  - Future improvement: apply a UHI delta-T correction derived from published Barcelona UHI studies (e.g. +1.5°C to nighttime summer dry bulb for zones with gridcode 5–6)

- **Verdict for our project:** **Primary.** This is the non-negotiable baseline climate input for every quantitative threshold in the rule engine — diurnal swing, cooling degree hours, peak solar radiation, wind availability hours, and running mean outdoor temperature for the comfort model. Its limitations are real, well-understood, and partially mitigated by dataset 4. Use as-is; disclose the airport siting bias prominently in the tool's output UI.
