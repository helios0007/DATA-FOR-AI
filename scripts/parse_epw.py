"""
parse_epw.py
============
Passive Design Advisor — Barcelona 2025
Parses a TMYx EPW file using pvlib and outputs the climate summary
statistics needed by the passive strategy rule engine.

Usage
-----
    python parse_epw.py path/to/file.epw [--output summary.json]

Outputs
-------
A JSON file (default: epw_summary.json) containing:
  - site metadata (lat, lon, elevation, timezone)
  - monthly stats: mean/max/min dry bulb, diurnal swing, GHI, wind speed
  - annual and summer cooling degree hours (CDH) above 26°C
  - running mean outdoor temperature for EN 16798-1 comfort model
  - wind rose summary (dominant directions and % calm)
  - night purge potential hours per summer month
  - EN 16798-1 and ASHRAE 55 comfort upper limits by month

Dependencies
------------
    pip install pvlib pandas numpy

Field notes (EPW column mapping — use pvlib, NOT raw column index)
-----------
  temp_air                   Dry bulb temperature (°C)
  temp_dew                   Dew point temperature (°C)
  relative_humidity          Relative humidity (%)
  ghi                        Global horizontal irradiance (Wh/m²)  ← NOT ghi_infrared
  dni                        Direct normal irradiance (Wh/m²)
  dhi                        Diffuse horizontal irradiance (Wh/m²)
  wind_speed                 Wind speed at 10 m (m/s)
  wind_direction             Wind direction in degrees (0–360°)     ← pvlib decodes from WMO encoding
  atmospheric_pressure       Station pressure (Pa)
  global_hor_illum           Global horizontal illuminance (lux)    ← NOT irradiance
  diffuse_horizontal_illum   Diffuse horizontal illuminance (lux)   ← NOT irradiance
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib


# ---------------------------------------------------------------------------
# Comfort standard thresholds (EN 16798-1:2019 and ASHRAE 55:2023)
# Adaptive model: upper comfort limit as a function of running mean outdoor
# temperature (θ_rm). Encoded from open-literature formulations.
# EN 16798-1 Category II:  θ_comfort_max = 0.33 × θ_rm + 18.8  (+ 2°C)
# ASHRAE 55 80% accept.:   θ_comfort_max = 0.31 × θ_rm + 17.8  (+ 3.5°C)
# ---------------------------------------------------------------------------

def en16798_upper_cat2(running_mean_temp: float) -> float:
    """EN 16798-1 Category II upper operative temperature limit (°C)."""
    return 0.33 * running_mean_temp + 18.8 + 2.0


def ashrae55_upper_80pct(running_mean_temp: float) -> float:
    """ASHRAE 55 80% acceptability upper operative temperature limit (°C)."""
    return 0.31 * running_mean_temp + 17.8 + 3.5


def running_mean_temperature(daily_means: pd.Series, alpha: float = 0.8) -> pd.Series:
    """
    Compute the exponentially weighted running mean outdoor temperature
    as defined in EN 16798-1 Annex A.

    θ_rm,n = (1 - α) × (θ_e,n-1 + α × θ_e,n-2 + α² × θ_e,n-3 + ...)

    Parameters
    ----------
    daily_means : pd.Series
        Daily mean outdoor dry bulb temperatures indexed by date.
        Must be indexed to a single continuous year (no multi-year gaps).
    alpha : float
        Smoothing constant (EN 16798-1 default = 0.8).

    Returns
    -------
    pd.Series
        Running mean temperature for each day, same index as input.
    """
    rm = pd.Series(index=daily_means.index, dtype=float)
    vals = daily_means.values
    n_history = 30  # 30 days of history is sufficient; α^30 < 0.001
    for i in range(len(vals)):
        n = min(i + 1, n_history)
        weights = np.array([(1 - alpha) * alpha ** k for k in range(n)])
        window = vals[max(0, i - n + 1):i + 1][::-1]
        w = weights[:len(window)]
        rm.iloc[i] = np.dot(window, w) / w.sum()
    return rm


# ---------------------------------------------------------------------------
# Core parser
# ---------------------------------------------------------------------------

def parse_epw(epw_path: str) -> dict:
    """
    Parse an EPW file and return a structured climate summary dict.

    Parameters
    ----------
    epw_path : str
        Path to the .epw file.

    Returns
    -------
    dict
        Nested dict with site metadata and all climate stats needed
        by the passive strategy rule engine.
    """
    path = Path(epw_path)
    if not path.exists():
        raise FileNotFoundError(f"EPW file not found: {epw_path}")

    # -- Read EPW with pvlib (handles all column mapping and encoding) -------
    df, meta = pvlib.iotools.read_epw(str(path))

    # pvlib returns a timezone-aware DatetimeIndex
    # Drop timezone for simpler groupby operations
    df.index = df.index.tz_localize(None)

    # IMPORTANT: TMYx months are drawn from different source years (e.g. Jan=1999,
    # Jul=2014). The real DatetimeIndex spans 1987–2020, so resample("D") by real
    # date would return NaN for months not present in a given year.
    # Fix: re-index to a synthetic single year (2001, non-leap) so all
    # month/day groupings work correctly.
    synthetic_index = pd.date_range("2001-01-01", periods=8760, freq="h")
    df.index = synthetic_index

    # -- Site metadata -------------------------------------------------------
    site = {
        "city":       meta.get("city", ""),
        "country":    meta.get("country", ""),
        "wmo_code":   meta.get("WMO_code", ""),
        "latitude":   meta.get("latitude"),
        "longitude":  meta.get("longitude"),
        "elevation_m": meta.get("altitude"),
        "timezone_utc_offset": meta.get("TZ"),
        "epw_file":   path.name,
    }

    # -- Convenience masks ---------------------------------------------------
    summer_mask = df.index.month.isin([6, 7, 8])   # JJA
    winter_mask = df.index.month.isin([12, 1, 2])  # DJF
    daytime_mask = df.index.hour.isin(range(6, 21))

    # -- Monthly stats -------------------------------------------------------
    monthly = {}
    for m in range(1, 13):
        mask = df.index.month == m
        sub = df[mask]

        # Diurnal swing: mean of (daily_max - daily_min) across all days
        daily_min = sub["temp_air"].resample("D").min()
        daily_max = sub["temp_air"].resample("D").max()
        swing = (daily_max - daily_min).mean()

        monthly[m] = {
            "temp_air_mean":    round(sub["temp_air"].mean(), 2),
            "temp_air_max":     round(sub["temp_air"].max(), 2),
            "temp_air_min":     round(sub["temp_air"].min(), 2),
            "diurnal_swing_mean_C": round(swing, 2),
            "rh_mean_pct":      round(sub["relative_humidity"].mean(), 1),
            "ghi_mean_Wh_m2":   round(sub["ghi"].mean(), 1),
            "ghi_peak_Wh_m2":   round(sub["ghi"].max(), 1),
            "dni_mean_Wh_m2":   round(sub["dni"].mean(), 1),
            "wind_speed_mean_m_s": round(sub["wind_speed"].mean(), 2),
            "wind_speed_max_m_s":  round(sub["wind_speed"].max(), 2),
        }

    # -- Cooling degree hours ------------------------------------------------
    base_temp = 26.0   # °C — threshold above which mechanical cooling need begins
    cdh_series = (df["temp_air"] - base_temp).clip(lower=0)

    cooling_degree_hours = {
        "base_temp_C":           base_temp,
        "annual_CDH":            round(cdh_series.sum(), 1),
        "summer_JJA_CDH":        round(cdh_series[summer_mask].sum(), 1),
        "peak_month":            int(cdh_series.groupby(df.index.month).sum().idxmax()),
    }

    # -- Running mean outdoor temperature (EN 16798-1) -----------------------
    daily_means = df["temp_air"].resample("D").mean()
    rm = running_mean_temperature(daily_means)

    # Map daily running mean back to monthly averages
    rm_monthly = {}
    for m in range(1, 13):
        mask_m = rm.index.month == m
        rm_val = round(rm[mask_m].mean(), 2)
        en_limit = round(en16798_upper_cat2(rm_val), 2)
        ashrae_limit = round(ashrae55_upper_80pct(rm_val), 2)
        rm_monthly[m] = {
            "running_mean_temp_C":       rm_val,
            "EN16798_upper_cat2_C":      en_limit,
            "ASHRAE55_upper_80pct_C":    ashrae_limit,
        }

    # -- Wind rose summary ---------------------------------------------------
    # Bin directions into 8 compass sectors using a vectorised approach
    # to avoid duplicate-label issues with pd.cut
    calms = ((df["wind_direction"] == 0) & (df["wind_speed"] == 0))
    non_calm = df[~calms]

    def direction_to_sector(deg):
        sectors = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((deg + 22.5) / 45) % 8
        return sectors[idx]

    sector_series = non_calm["wind_direction"].apply(direction_to_sector)
    sector_counts = sector_series.value_counts()

    wind_rose = {
        sector: round(count / len(df) * 100, 1)
        for sector, count in sector_counts.items()
    }
    wind_rose["calm_pct"] = round(calms.sum() / len(df) * 100, 1)

    # Dominant wind directions (top 2)
    sorted_sectors = sorted(
        [(k, v) for k, v in wind_rose.items() if k != "calm_pct"],
        key=lambda x: x[1],
        reverse=True
    )
    dominant_directions = [s[0] for s in sorted_sectors[:2]]

    wind_summary = {
        "dominant_directions":    dominant_directions,
        "sector_pct":             wind_rose,
        "annual_mean_speed_m_s":  round(df["wind_speed"].mean(), 2),
        "summer_mean_speed_m_s":  round(df[summer_mask]["wind_speed"].mean(), 2),
        "hours_above_1ms_annual_pct": round(
            (df["wind_speed"] >= 1.0).sum() / len(df) * 100, 1
        ),
        "hours_above_1ms_summer_pct": round(
            (df[summer_mask]["wind_speed"] >= 1.0).sum() / summer_mask.sum() * 100, 1
        ),
    }

    # -- Night purge potential -----------------------------------------------
    # Hours after 20:00 where outdoor temp < threshold (cool enough to flush heat)
    night_mask = df.index.hour >= 20
    night_purge = {}
    for threshold, label in [(20, "below_20C"), (22, "below_22C"), (24, "below_24C")]:
        summer_night = df[summer_mask & night_mask]
        count = int((summer_night["temp_air"] < threshold).sum())
        pct = round(count / len(summer_night) * 100, 1)
        night_purge[label] = {
            "hours": count,
            "pct_of_summer_night_hours": pct,
        }

    # -- Solar radiation summary (for shading strategy) ----------------------
    solar = {
        "annual_mean_GHI_Wh_m2":  round(df["ghi"].mean(), 1),
        "summer_mean_GHI_Wh_m2":  round(df[summer_mask]["ghi"].mean(), 1),
        "summer_peak_GHI_Wh_m2":  round(df[summer_mask]["ghi"].max(), 1),
        "summer_mean_DNI_Wh_m2":  round(df[summer_mask]["dni"].mean(), 1),
        "annual_mean_DHI_Wh_m2":  round(df["dhi"].mean(), 1),
        # Hours with significant solar load (GHI > 200 Wh/m²) in summer
        "summer_hours_GHI_above_200_Wh_m2": int(
            (df[summer_mask]["ghi"] > 200).sum()
        ),
    }

    # -- Assemble output -----------------------------------------------------
    summary = {
        "site":                     site,
        "monthly_stats":            monthly,
        "cooling_degree_hours":     cooling_degree_hours,
        "comfort_thresholds":       rm_monthly,
        "wind":                     wind_summary,
        "night_purge_potential":    night_purge,
        "solar":                    solar,
        # Key rule-engine flags derived from the data
        "rule_engine_inputs": {
            "july_diurnal_swing_C":       monthly[7]["diurnal_swing_mean_C"],
            "summer_mean_temp_C":         round(
                df[summer_mask]["temp_air"].mean(), 2
            ),
            "summer_peak_temp_C":         round(
                df[summer_mask]["temp_air"].max(), 2
            ),
            "summer_CDH_above_26C":       cooling_degree_hours["summer_JJA_CDH"],
            "dominant_wind_direction":    dominant_directions[0] if dominant_directions else None,
            "summer_mean_wind_m_s":       wind_summary["summer_mean_speed_m_s"],
            "night_purge_hours_below_22C": night_purge["below_22C"]["hours"],
            "july_EN16798_upper_C":       rm_monthly[7]["EN16798_upper_cat2_C"],
            "july_ASHRAE55_upper_C":      rm_monthly[7]["ASHRAE55_upper_80pct_C"],
        },
    }

    return summary


# ---------------------------------------------------------------------------
# JSON serialisation helper (numpy/pandas types → native Python)
# ---------------------------------------------------------------------------

def _json_default(obj):
    """Convert numpy and pandas scalar types to native Python for json.dump."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serialisable")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    # Paths are relative to this script's location.
    # Repo structure assumed:
    #   scripts/parse_epw.py      <- this file
    #   data/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw
    #   outputs/epw_summary.json
    _here = Path(__file__).parent
    default_epw = _here.parent / "data" / "ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw"
    default_out = _here.parent / "outputs" / "epw_summary.json"

    parser = argparse.ArgumentParser(
        description="Parse a TMYx EPW file into a climate summary JSON "
                    "for the Passive Design Advisor rule engine."
    )
    parser.add_argument(
        "epw_path",
        nargs="?",
        default=str(default_epw),
        help="Path to the .epw file (default: %(default)s)"
    )
    parser.add_argument(
        "--output", "-o",
        default=str(default_out),
        help="Output JSON file path (default: %(default)s)"
    )
    args = parser.parse_args()

    print(f"Parsing: {args.epw_path}")
    summary = parse_epw(args.epw_path)

    out_path = Path(args.output)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False, default=_json_default)

    print(f"Summary written to: {out_path}")

    # Print key rule-engine inputs to console
    re = summary["rule_engine_inputs"]
    print("\n── Key rule-engine inputs ──────────────────────────────")
    for k, v in re.items():
        print(f"  {k:<40} {v}")


if __name__ == "__main__":
    main()
