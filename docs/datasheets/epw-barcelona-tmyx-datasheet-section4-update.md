## 4. Preprocessing & cleaning — updated for Session 3

### What preprocessing was done by the dataset creators?

The TMYx EPW file was already preprocessed before publication: hourly airport observations were quality-controlled, converted to the EnergyPlus Weather format, and assembled into a typical meteorological year. Solar radiation fields were derived or completed through reanalysis/model-based methods. The file also includes an EPW metadata header with location, design conditions, and auxiliary climate information.

### Is the raw data also available?

Yes. The underlying source observations are available through NOAA/NCEI ISD, while the EPW file used in this project is downloaded from the Ladybug Tools EPW map / climate.onebuilding.org mirror.

### What preprocessing did WE do before adopting the dataset?

For Session 3, we treated this EPW file as the **primary dataset** and produced a deterministic cleaned climate table:

1. Loaded the `.epw` file after skipping the 8-line EPW metadata header.
2. Applied an explicit EPW column schema to avoid confusing radiation fields with illuminance or extraterrestrial radiation fields.
3. Confirmed the file contains **8,760 hourly records**.
4. Selected only the variables required by the Passive Design Advisor:
   - dry bulb temperature
   - dew point temperature
   - relative humidity
   - GHI / DNI / DHI
   - wind direction
   - wind speed
   - sky cover
   - month / day / hour / source year
5. Coerced selected variables into numeric types.
6. Constructed a deterministic synthetic timestamp from month/day/hour.
7. Preserved `source_year` and `hour_raw_epw` for traceability.
8. Validated physical ranges for temperature, humidity, wind, direction, sky cover, and radiation.
9. Added passive-design derived fields:
   - `is_summer`
   - `is_cooling_season`
   - `is_night`
   - `cooling_degree_c_above_26`
   - `overheating_hour_proxy_26c`
   - `solar_radiation_total_wh_m2`
   - `wind_available_flag_1p5ms`
   - `night_purge_candidate_flag`
10. Saved the cleaned output as:

```text
data/processed/barcelona-epw-tmyx-clean.parquet
```

### Where is the preprocessing software / code available?

```text
notebooks/02-data-cleaning.ipynb
src/clean_data.py
docs/data-cleaning-log.md
docs/pipeline-architecture-v1.md
```

### Cleaning decision statement

We did **not** impute, clip, or alter the selected primary climate variables because profiling showed the key fields are complete and physically plausible. The cleaning process mainly standardises schema, validates fields, constructs reproducible time indexing, and derives passive-design indicators.

### Important limitation retained after cleaning

The cleaned EPW remains a **single-point airport climate dataset**. It does not represent central Barcelona microclimate by itself. Urban heat island, canyon wind reduction, obstruction, vegetation, and roof exposure must be handled by supporting datasets such as Open Data BCN Thermal Comfort Zones, ICGC Alçades, OSM, and Copernicus Street Tree Layer.
