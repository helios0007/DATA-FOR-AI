"""clean_data.py — deterministic cleaning pipeline for the Barcelona EPW / TMYx weather file.

Run from project root:
    python src/clean_data.py
"""

from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

RAW_PATH = Path("data/raw/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw")
OUT_PATH = Path("data/processed/barcelona-epw-tmyx-clean.parquet")
SYNTHETIC_YEAR = 2025
RANDOM_SEED = 42

EPW_COLUMNS = [
    "source_year", "month", "day", "hour", "minute",
    "data_source_uncertainty",
    "dry_bulb_temp_c", "dew_point_temp_c", "relative_humidity_pct",
    "atmospheric_pressure_pa",
    "extraterrestrial_horizontal_radiation_wh_m2",
    "extraterrestrial_direct_normal_radiation_wh_m2",
    "horizontal_infrared_radiation_wh_m2",
    "global_horizontal_radiation_wh_m2",
    "direct_normal_radiation_wh_m2",
    "diffuse_horizontal_radiation_wh_m2",
    "global_horizontal_illuminance_lux",
    "direct_normal_illuminance_lux",
    "diffuse_horizontal_illuminance_lux",
    "zenith_luminance_cd_m2",
    "wind_direction_deg",
    "wind_speed_m_s",
    "total_sky_cover_tenths",
    "opaque_sky_cover_tenths",
    "visibility_km",
    "ceiling_height_m",
    "present_weather_observation",
    "present_weather_codes",
    "precipitable_water_mm",
    "aerosol_optical_depth_thousandths",
    "snow_depth_cm",
    "days_since_last_snowfall",
    "albedo",
    "liquid_precipitation_depth_mm",
    "liquid_precipitation_quantity_hr",
]

SELECTED_COLUMNS = [
    "source_year", "month", "day", "hour",
    "dry_bulb_temp_c", "dew_point_temp_c", "relative_humidity_pct",
    "global_horizontal_radiation_wh_m2",
    "direct_normal_radiation_wh_m2",
    "diffuse_horizontal_radiation_wh_m2",
    "wind_direction_deg", "wind_speed_m_s",
    "total_sky_cover_tenths",
    "opaque_sky_cover_tenths",
]
NUMERIC_COLUMNS = SELECTED_COLUMNS.copy()

FINAL_COLUMNS = [
    "timestamp", "source_year", "month", "day", "hour_raw_epw", "hour_of_day",
    "dry_bulb_temp_c", "dew_point_temp_c", "relative_humidity_pct",
    "global_horizontal_radiation_wh_m2", "direct_normal_radiation_wh_m2",
    "diffuse_horizontal_radiation_wh_m2", "wind_direction_deg", "wind_speed_m_s",
    "total_sky_cover_tenths", "opaque_sky_cover_tenths",
    "is_summer", "is_cooling_season", "is_night",
    "cooling_degree_c_above_26", "overheating_hour_proxy_26c",
    "solar_radiation_total_wh_m2", "wind_available_flag_1p5ms",
    "night_purge_candidate_flag",
]


def read_epw(path: Path = RAW_PATH) -> pd.DataFrame:
    """Read an EPW file into a dataframe with named EPW columns.

    Args:
        path: Path to the raw EPW file.

    Returns:
        Dataframe with 8,760 hourly rows and EPW columns.

    Raises:
        FileNotFoundError: If the EPW file does not exist.
        ValueError: If the file does not contain 8,760 rows.

    Example:
        >>> df_raw = read_epw(RAW_PATH)
        >>> len(df_raw) == 8760
        True
    """
    if not path.exists():
        raise FileNotFoundError(f"Missing EPW file: {path}")
    df = pd.read_csv(path, skiprows=8, header=None, names=EPW_COLUMNS)
    if len(df) != 8760:
        raise ValueError(f"Expected 8,760 hourly rows, got {len(df):,}")
    return df


def select_epw_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Select only EPW fields required by the passive design advisor.

    Args:
        df: Raw EPW dataframe with all EPW columns.

    Returns:
        Dataframe with project-relevant climate fields.

    Raises:
        ValueError: If expected EPW columns are missing.

    Example:
        >>> selected = select_epw_fields(df_raw)
        >>> set(SELECTED_COLUMNS).issubset(selected.columns)
        True
    """
    missing = set(SELECTED_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing EPW columns: {missing}")
    return df[SELECTED_COLUMNS].copy()


def coerce_epw_numeric_fields(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce selected EPW fields to numeric values.

    Args:
        df: Dataframe with selected EPW fields.

    Returns:
        Dataframe with numeric climate fields.

    Raises:
        ValueError: If any required numeric field cannot be parsed.

    Example:
        >>> clean = coerce_epw_numeric_fields(selected)
        >>> clean[NUMERIC_COLUMNS].notna().all().all()
        True
    """
    out = df.copy()
    for col in NUMERIC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if not out[NUMERIC_COLUMNS].notna().all().all():
        missing = out[NUMERIC_COLUMNS].isna().sum()
        missing = missing[missing > 0].to_dict()
        raise ValueError(f"Numeric parse failures: {missing}")
    return out


def construct_epw_timestamp(df: pd.DataFrame) -> pd.DataFrame:
    """Construct a deterministic synthetic timestamp from EPW month/day/hour.

    Args:
        df: Dataframe with month, day, and EPW hour values.

    Returns:
        Dataframe with timestamp, hour_raw_epw, and hour_of_day.

    Raises:
        ValueError: If timestamp construction fails.

    Example:
        >>> out = construct_epw_timestamp(df)
        >>> out["timestamp"].notna().all()
        True
    """
    required = {"month", "day", "hour"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing timestamp columns: {missing}")
    out = df.copy()
    out["hour_raw_epw"] = out["hour"].astype("int16")
    out["hour_of_day"] = (out["hour_raw_epw"] - 1).astype("int8")
    out["timestamp"] = pd.to_datetime(
        {"year": SYNTHETIC_YEAR, "month": out["month"].astype(int),
         "day": out["day"].astype(int), "hour": out["hour_of_day"].astype(int)},
        errors="coerce",
    )
    if not out["timestamp"].notna().all():
        raise ValueError("Timestamp construction produced null values.")
    out = out.sort_values("timestamp").reset_index(drop=True)
    if not out["timestamp"].is_monotonic_increasing:
        raise ValueError("Timestamp order is not monotonic after sorting.")
    return out


def validate_epw_physical_ranges(df: pd.DataFrame) -> pd.DataFrame:
    """Validate physical ranges for selected EPW climate variables.

    Args:
        df: Dataframe with numeric climate fields.

    Returns:
        A copy of the dataframe if all checks pass.

    Raises:
        ValueError: If a field violates expected physical ranges.

    Example:
        >>> valid = validate_epw_physical_ranges(df)
        >>> len(valid) == len(df)
        True
    """
    checks = {
        "dry_bulb_temp_c": df["dry_bulb_temp_c"].between(-20, 50).all(),
        "dew_point_temp_c": df["dew_point_temp_c"].between(-30, 35).all(),
        "relative_humidity_pct": df["relative_humidity_pct"].between(0, 100).all(),
        "wind_direction_deg": df["wind_direction_deg"].between(0, 360).all(),
        "wind_speed_m_s": df["wind_speed_m_s"].between(0, 60).all(),
        "global_horizontal_radiation_wh_m2": (df["global_horizontal_radiation_wh_m2"] >= 0).all(),
        "direct_normal_radiation_wh_m2": (df["direct_normal_radiation_wh_m2"] >= 0).all(),
        "diffuse_horizontal_radiation_wh_m2": (df["diffuse_horizontal_radiation_wh_m2"] >= 0).all(),
        "total_sky_cover_tenths": df["total_sky_cover_tenths"].between(0, 10).all(),
        "opaque_sky_cover_tenths": df["opaque_sky_cover_tenths"].between(0, 10).all(),
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"Physical range validation failed for: {failed}")
    return df.copy()


def add_passive_design_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add interpretable passive-design indicators from EPW climate fields.

    Args:
        df: Validated EPW climate dataframe.

    Returns:
        Dataframe with cooling, summer, wind, and night-purge indicators.

    Example:
        >>> out = add_passive_design_features(df)
        >>> "overheating_hour_proxy_26c" in out.columns
        True
    """
    out = df.copy()
    out["month"] = out["month"].astype("int8")
    out["day"] = out["day"].astype("int8")
    out["is_summer"] = out["month"].isin([6, 7, 8])
    out["is_cooling_season"] = out["month"].isin([5, 6, 7, 8, 9])
    out["is_night"] = (out["hour_of_day"] >= 20) | (out["hour_of_day"] <= 6)
    out["cooling_degree_c_above_26"] = (out["dry_bulb_temp_c"] - 26).clip(lower=0)
    out["overheating_hour_proxy_26c"] = out["dry_bulb_temp_c"] > 26
    out["solar_radiation_total_wh_m2"] = (
        out["global_horizontal_radiation_wh_m2"]
        + out["direct_normal_radiation_wh_m2"]
        + out["diffuse_horizontal_radiation_wh_m2"]
    )
    out["wind_available_flag_1p5ms"] = out["wind_speed_m_s"] >= 1.5
    out["night_purge_candidate_flag"] = (
        out["is_night"] & out["is_summer"] & (out["dry_bulb_temp_c"] <= 22)
    )
    if not (out["cooling_degree_c_above_26"] >= 0).all():
        raise ValueError("Cooling degree values must be non-negative.")
    return out


def format_final_schema(df: pd.DataFrame) -> pd.DataFrame:
    """Select, order, and validate the final cleaned EPW schema.

    Args:
        df: Dataframe containing base and derived columns.

    Returns:
        Final cleaned dataframe ready for parquet.

    Raises:
        ValueError: If final columns are missing or row count changes.

    Example:
        >>> final = format_final_schema(df)
        >>> len(final) == 8760
        True
    """
    missing = set(FINAL_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Missing final columns: {missing}")
    out = df[FINAL_COLUMNS].sort_values("timestamp").reset_index(drop=True)
    if len(out) != 8760:
        raise ValueError(f"Expected 8,760 final rows, got {len(out):,}")
    return out


def assert_clean_invariants(df: pd.DataFrame) -> None:
    """Assert final properties required by downstream components.

    Args:
        df: Final cleaned EPW dataframe.

    Returns:
        None. Raises an assertion error if an invariant fails.

    Example:
        >>> assert_clean_invariants(df_clean)
    """
    assert len(df) == 8760, "Clean EPW must have 8,760 rows."
    assert df["timestamp"].notna().all(), "timestamp contains nulls."
    assert df["dry_bulb_temp_c"].between(-20, 50).all(), "temperature out of range."
    assert df["relative_humidity_pct"].between(0, 100).all(), "RH out of range."
    assert df["wind_speed_m_s"].between(0, 60).all(), "wind speed out of range."
    assert set(FINAL_COLUMNS).issubset(df.columns), "Final columns missing."


def clean_epw_dataset(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Run the full EPW cleaning pipeline from raw dataframe to final dataframe.

    Args:
        df_raw: Raw EPW dataframe produced by read_epw.

    Returns:
        Cleaned EPW dataframe with the final schema.

    Example:
        >>> df_raw = read_epw(RAW_PATH)
        >>> df_clean = clean_epw_dataset(df_raw)
        >>> len(df_clean)
        8760
    """
    np.random.seed(RANDOM_SEED)
    df_clean = (
        df_raw
        .pipe(select_epw_fields)
        .pipe(coerce_epw_numeric_fields)
        .pipe(construct_epw_timestamp)
        .pipe(validate_epw_physical_ranges)
        .pipe(add_passive_design_features)
        .pipe(format_final_schema)
    )
    assert_clean_invariants(df_clean)
    return df_clean


def main() -> None:
    """Run the EPW cleaning pipeline from the command line."""
    print(f"Loading {RAW_PATH}...")
    df_raw = read_epw(RAW_PATH)
    print(f"Raw shape: {df_raw.shape}")
    df_clean = clean_epw_dataset(df_raw)
    print(f"Cleaned shape: {df_clean.shape}")
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_parquet(OUT_PATH, index=False)
    print(f"Wrote {OUT_PATH} ({OUT_PATH.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
