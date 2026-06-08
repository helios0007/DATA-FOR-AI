"""Shared helpers used across multiple pipeline stages."""

import json
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point

EPW_SUMMARY_PATH = Path("outputs/epw_summary.json")


def load_epw_summary(path: Path = EPW_SUMMARY_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def latlon_to_utm31n(lat: float, lon: float) -> Point:
    """Convert WGS84 lat/lon to EPSG:25831 (UTM zone 31N) Point."""
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:25831", always_xy=True)
    x, y = transformer.transform(lon, lat)
    return Point(x, y)


def linear_ramp(x: float, x_min: float, x_max: float) -> float:
    """
    Linear ramp membership function.
    Returns 0 at x <= x_min, 1 at x >= x_max, linear between.
    Source: MAUT fuzzy membership — spec §8.
    """
    if x <= x_min:
        return 0.0
    if x >= x_max:
        return 1.0
    return (x - x_min) / (x_max - x_min)


def inverse_ramp(x: float, x_good: float, x_bad: float) -> float:
    """Compliance decreases as x increases from x_good toward x_bad."""
    return 1.0 - linear_ramp(x, x_good, x_bad)
