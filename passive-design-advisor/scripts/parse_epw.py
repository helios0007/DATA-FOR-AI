"""
parse_epw.py — Parses the Barcelona TMYx EPW file and writes outputs/epw_summary.json.
All statistics are computed for JJA (June–August) unless otherwise noted.

Run from project root:
    python scripts/parse_epw.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pvlib

EPW_PATH = Path("data/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw")
OUTPUT_PATH = Path("outputs/epw_summary.json")

WIND_COMPASS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def wind_deg_to_label(deg: float) -> str:
    idx = int((float(deg) + 11.25) / 22.5) % 16
    return WIND_COMPASS[idx]


def compute_en16798_running_mean(daily_means: pd.Series, alpha: float = 0.8) -> pd.Series:
    """
    EN 16798-1:2019 Annex B exponentially weighted running mean.
    T_rm,n = (1-α) * Σ_{k=1}^{∞} α^(k-1) * T_ed-k
    Truncated to 30 previous days.
    """
    values = daily_means.values
    rm = np.zeros(len(values))
    for i in range(len(values)):
        s = 0.0
        w_total = 0.0
        for k in range(1, min(i + 1, 31)):
            w = alpha ** (k - 1)
            s += w * values[i - k]
            w_total += w
        rm[i] = (1 - alpha) * s if w_total > 0 else values[i]
    return pd.Series(rm, index=daily_means.index)


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    df, meta = pvlib.iotools.read_epw(str(EPW_PATH), coerce_year=2001)
    df.index = pd.date_range(
        start="2001-01-01 00:00",
        periods=8760,
        freq="h",
        tz="Etc/GMT-1",
    )

    summer = df[df.index.month.isin([6, 7, 8])].copy()
    july   = df[df.index.month == 7].copy()
    june   = df[df.index.month == 6].copy()

    # ── Summer basics ────────────────────────────────────────────────────────
    summer_mean_temp = float(summer["temp_air"].mean())
    summer_peak_temp = float(summer["temp_air"].max())
    summer_cdh       = float((summer["temp_air"] - 26).clip(lower=0).sum())
    summer_mean_wind = float(summer["wind_speed"].mean())
    summer_mean_ghi  = float(summer["ghi"].mean())
    summer_peak_ghi  = float(summer["ghi"].max())

    # ── July diurnal swing (mean of daily max − min) ─────────────────────────
    july_daily  = july["temp_air"].resample("D").agg(["max", "min"])
    july_swing  = float((july_daily["max"] - july_daily["min"]).mean())

    # ── Dominant summer wind direction ───────────────────────────────────────
    calm_mask = summer["wind_speed"] > 0.5   # exclude calm hours from direction calc
    wind_labels = summer.loc[calm_mask, "wind_direction"].apply(wind_deg_to_label)
    dominant_wind = wind_labels.value_counts().idxmax() if len(wind_labels) > 0 else "N"

    # ── Night purge hours: JJA nights (20:00–06:59) where T < 22°C ──────────
    night_mask = summer.index.hour.isin(list(range(0, 7)) + list(range(20, 24)))
    night_purge_hours = int((summer.loc[night_mask, "temp_air"] < 22).sum())

    # ── EN 16798-1:2019 adaptive upper limit for July (Category II) ──────────
    # Category II: T_upper = 0.33 * T_rm + 18.8 + 2
    daily_means = df["temp_air"].resample("D").mean()
    running_mean = compute_en16798_running_mean(daily_means)

    july_day_index = pd.date_range("2001-07-01", "2001-07-31", freq="D")
    july_rm_vals = running_mean[running_mean.index.isin(july_day_index)]
    july_rm_mean = float(july_rm_vals.mean()) if len(july_rm_vals) > 0 else float(daily_means[daily_means.index.month == 7].mean())
    july_en16798_upper = round(0.33 * july_rm_mean + 18.8 + 2.0, 2)

    # ── ASHRAE 55:2023 adaptive upper limit for July (80% acceptability) ─────
    # T_upper = 0.31 * T_pma + 21.3 + 2.0
    # T_pma ≈ June mean outdoor dry-bulb (prevailing mean of preceding month)
    june_mean_temp = float(june["temp_air"].mean())
    july_ashrae55_upper = round(0.31 * june_mean_temp + 21.3 + 2.0, 2)

    summary = {
        "epw_file": str(EPW_PATH),
        "location": {
            "latitude":    meta.get("latitude"),
            "longitude":   meta.get("longitude"),
            "elevation_m": meta.get("altitude"),
            "timezone":    meta.get("TZ"),
        },
        "july_diurnal_swing_C":      round(july_swing, 2),
        "summer_mean_temp_C":         round(summer_mean_temp, 2),
        "summer_peak_temp_C":         round(summer_peak_temp, 2),
        "summer_CDH_above_26C":       round(summer_cdh, 1),
        "dominant_wind_direction":    dominant_wind,
        "summer_mean_wind_m_s":       round(summer_mean_wind, 2),
        "night_purge_hours_below_22C": night_purge_hours,
        "july_EN16798_upper_C":       july_en16798_upper,
        "july_ASHRAE55_upper_C":      july_ashrae55_upper,
        "summer_mean_GHI_Wh_m2":      round(summer_mean_ghi, 1),
        "summer_peak_GHI_Wh_m2":      round(summer_peak_ghi, 1),
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"EPW summary written to {OUTPUT_PATH}\n")
    for k, v in summary.items():
        if k not in ("epw_file", "location"):
            print(f"  {k:35s}: {v}")


if __name__ == "__main__":
    main()
