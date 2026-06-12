"""
Stage 2 — Context Enrichment from Geospatial Data
Attaches urban morphology (SVF, canyon H/W, obstruction angles) and
climate context (EPW summary) to the building features from Stage 1.
All spatial operations use EPSG:25831 (UTM zone 31N).
"""

from dataclasses import dataclass
from functools import lru_cache

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from src.utils import latlon_to_utm31n, load_epw_summary, resolve_path

# ── Dataset paths ────────────────────────────────────────────────────────────
BUILDINGS_GPKG  = "data/Base - Alçades.gpkg"
BUILDINGS_LAYER = "Base - Alçades"
COMFORT_GPKG    = "data/confort_termic_od.gpkg"

PRIMARY_NIVELL  = "CON_01pol_PL"
SEARCH_RADIUS_M = 150

COMFORT_LABELS = {
    1: "Very High",
    2: "High",
    3: "Medium",
    4: "Medium-Low",
    5: "Low",
    6: "Very Low",
}

ORIENTATION_BEARINGS = {
    "N": 0, "NE": 45, "E": 90, "SE": 135,
    "S": 180, "SW": 225, "W": 270, "NW": 315,
}


# ── Data class ───────────────────────────────────────────────────────────────

@dataclass
class SiteContext:
    # Urban morphology
    svf_mean: float
    canyon_hw_ratio: float
    canyon_wind_correction: float
    surrounding_heights_m: list[float]
    solar_obstruction_angles: dict[str, float]
    green_cover_ratio_50m: float

    # Thermal comfort zone
    thermal_comfort_gridcode: int
    thermal_comfort_label: str

    # Climate (from epw_summary.json)
    july_diurnal_swing_C: float
    summer_mean_temp_C: float
    summer_peak_temp_C: float
    summer_CDH_above_26C: float
    dominant_wind_direction: str
    summer_mean_wind_m_s: float
    night_purge_hours_below_22C: int
    july_EN16798_upper_C: float
    july_ASHRAE55_upper_C: float
    summer_mean_GHI_Wh_m2: float
    summer_peak_GHI_Wh_m2: float


# ── Building data loading ─────────────────────────────────────────────────────

@lru_cache(maxsize=2)
def load_buildings(gpkg_path: str = BUILDINGS_GPKG) -> gpd.GeoDataFrame:
    """
    Load ICGC building footprints with heights.
    Filters to primary level and computes height_m = Z_MAX_VOL - Z_MIN_VOL.
    Cached: the GPKG is ~180 MB, so re-reading it per request dominated
    enrichment time (~5 s/call). Callers must not mutate the returned frame.
    """
    gdf = gpd.read_file(resolve_path(gpkg_path), layer=BUILDINGS_LAYER)
    gdf = gdf[gdf["NIVELL"] == PRIMARY_NIVELL].copy()
    gdf["height_m"] = gdf["Z_MAX_VOL"] - gdf["Z_MIN_VOL"]
    gdf = gdf[gdf["height_m"] > 1.0].copy()
    return gdf


# ── SVF calculation ───────────────────────────────────────────────────────────

def compute_svf(
    site_point: Point,
    buildings_gdf: gpd.GeoDataFrame,
    site_height_m: float = 1.5,
) -> float:
    """
    Simplified SVF from surrounding building obstruction angles.
    SVF = 1 - (1/2π) × Σ sin²(α_i) × Δθ_i

    Source: Lindberg et al. 2018, Urban Climate 24:688–701.
    """
    buffer = site_point.buffer(SEARCH_RADIUS_M)
    nearby = buildings_gdf[buildings_gdf.geometry.intersects(buffer)].copy()

    if len(nearby) == 0:
        return 1.0

    n_sectors = 36
    delta_theta = 2 * np.pi / n_sectors
    svf_sum = 0.0

    for i in range(n_sectors):
        angle_rad = i * delta_theta
        max_alpha = 0.0

        for _, row in nearby.iterrows():
            centroid = row.geometry.centroid
            dist = site_point.distance(centroid)
            if dist < 1.0:
                continue
            bearing = np.arctan2(
                centroid.x - site_point.x,
                centroid.y - site_point.y,
            )
            sector_diff = abs(((bearing - angle_rad + np.pi) % (2 * np.pi)) - np.pi)
            if sector_diff < delta_theta / 2:
                h = max(0.0, row["height_m"] - site_height_m)
                alpha = np.arctan2(h, dist)
                max_alpha = max(max_alpha, alpha)

        svf_sum += np.sin(max_alpha) ** 2 * delta_theta

    return float(np.clip(1.0 - svf_sum / (2 * np.pi), 0.0, 1.0))


# ── Canyon H/W and wind correction ───────────────────────────────────────────

def get_canyon_hw_ratio(
    site_point: Point,
    buildings_gdf: gpd.GeoDataFrame,
    search_radius_m: float = 50.0,
) -> float:
    """
    H/W ratio: mean building height within 50m / estimated street width.
    Street width estimated as twice the distance from site_point to the
    nearest building perimeter (open-space half-width × 2).
    Falls back to H/W = 1.0 if insufficient data.
    """
    buffer = site_point.buffer(search_radius_m)
    nearby = buildings_gdf[buildings_gdf.geometry.intersects(buffer)].copy()

    if len(nearby) == 0:
        return 0.5

    mean_height = float(nearby["height_m"].mean())

    # Nearest building perimeter distance
    min_dist = float(nearby.geometry.apply(
        lambda geom: geom.boundary.distance(site_point)
    ).min())
    street_width = max(2.0 * min_dist, 3.0)  # at least 3m

    return round(mean_height / street_width, 2)


def get_canyon_wind_correction(hw_ratio: float) -> float:
    """
    Wind speed correction factor for street canyon geometry.
    v_canyon = v_EPW × correction_factor

    Source: Blocken B. et al. 2007, J. Wind Eng. Ind. Aerodyn. 95(9):941–962, Table 3.
    """
    if hw_ratio < 0.5:
        return 0.9
    elif hw_ratio < 1.0:
        return 0.7
    elif hw_ratio < 2.0:
        return 0.5
    else:
        return 0.3


# ── Solar obstruction angles ─────────────────────────────────────────────────

def compute_obstruction_angles(
    site_point: Point,
    buildings_gdf: gpd.GeoDataFrame,
    site_height_m: float = 10.0,
) -> dict[str, float]:
    """
    For each compass orientation, compute the maximum solar obstruction angle
    (elevation angle above horizon blocked by surrounding buildings).

    Source: Szokolay S.V. 2004, Introduction to Architectural Science, §2.3.
    """
    result: dict[str, float] = {}
    sector_half = np.radians(22.5)

    for label, bearing_deg in ORIENTATION_BEARINGS.items():
        bearing_rad = np.radians(bearing_deg)
        max_angle = 0.0

        for _, row in buildings_gdf.iterrows():
            centroid = row.geometry.centroid
            dist = site_point.distance(centroid)
            if dist < 1.0:
                continue
            b = np.arctan2(
                centroid.x - site_point.x,
                centroid.y - site_point.y,
            )
            diff = abs(((b - bearing_rad + np.pi) % (2 * np.pi)) - np.pi)
            if diff < sector_half:
                h = max(0.0, row["height_m"] - site_height_m)
                alpha = np.degrees(np.arctan2(h, dist))
                max_angle = max(max_angle, alpha)

        result[label] = round(max_angle, 1)

    return result


# ── Green cover ratio ─────────────────────────────────────────────────────────

def estimate_green_cover(
    site_point: Point,
    buildings_gdf: gpd.GeoDataFrame,
    radius_m: float = 50.0,
) -> float:
    """
    Approximate green cover as fraction of 50m buffer not covered by building footprints.
    A dense urban block (BCN average) typically yields 0.05–0.15.
    """
    buffer = site_point.buffer(radius_m)
    buffer_area = buffer.area

    nearby = buildings_gdf[buildings_gdf.geometry.intersects(buffer)].copy()
    if len(nearby) == 0:
        return 0.3  # open site

    # Clip building footprints to buffer and sum areas
    clipped_area = nearby.geometry.intersection(buffer).area.sum()
    built_fraction = min(1.0, clipped_area / buffer_area)
    # Assume remaining non-built area is ~40% road, 60% potential green
    green_fraction = max(0.0, (1.0 - built_fraction) * 0.6)
    return round(float(green_fraction), 3)


# ── Thermal comfort zone ──────────────────────────────────────────────────────

@lru_cache(maxsize=2)
def _load_comfort_zones(gpkg_path: str = COMFORT_GPKG) -> gpd.GeoDataFrame:
    """Load and reproject the comfort-zone polygons once per process."""
    return gpd.read_file(resolve_path(gpkg_path)).to_crs("EPSG:25831")


def get_thermal_comfort_zone(
    site_point: Point,
    gpkg_path: str = COMFORT_GPKG,
) -> tuple[int, str]:
    """
    Point-in-polygon lookup against confort_termic_od.gpkg.
    Returns (gridcode, label).
    gridcode 1 = Very High comfort (coolest); 6 = Very Low comfort (hottest).

    Source: Ajuntament de Barcelona, Open Data BCN — confort-termic dataset.
    """
    gdf = _load_comfort_zones(gpkg_path)

    matches = gdf[gdf.geometry.contains(site_point)]
    if len(matches) == 0:
        gdf = gdf.copy()
        gdf["_dist"] = gdf.geometry.distance(site_point)
        matches = gdf.nsmallest(1, "_dist")

    gridcode = int(matches.iloc[0]["gridcode"])
    gridcode = max(1, min(6, gridcode))
    return gridcode, COMFORT_LABELS[gridcode]


# ── Main enricher ─────────────────────────────────────────────────────────────

def enrich(
    site_lat: float,
    site_lon: float,
    building_height_m: float = 10.0,
    epw_summary_path: str = "outputs/epw_summary.json",
    buildings_gpkg: str = BUILDINGS_GPKG,
    comfort_gpkg: str = COMFORT_GPKG,
) -> SiteContext:
    """
    Build and return SiteContext for the given site coordinates.
    building_height_m: approximate height of the subject building (for obstruction calc).
    """
    site_point = latlon_to_utm31n(site_lat, site_lon)

    # Load datasets
    buildings = load_buildings(buildings_gpkg)

    # Filter to search radius for efficiency
    buffer_large = site_point.buffer(SEARCH_RADIUS_M + 50)
    nearby_all = buildings[buildings.geometry.intersects(buffer_large)].copy()

    # Urban morphology
    svf = compute_svf(site_point, nearby_all)
    hw_ratio = get_canyon_hw_ratio(site_point, nearby_all)
    wind_correction = get_canyon_wind_correction(hw_ratio)
    obstruction = compute_obstruction_angles(site_point, nearby_all, site_height_m=building_height_m)
    green_cover = estimate_green_cover(site_point, nearby_all)

    nearby_heights = nearby_all["height_m"].tolist()

    # Thermal comfort zone
    gridcode, comfort_label = get_thermal_comfort_zone(site_point, comfort_gpkg)

    # EPW climate summary
    epw = load_epw_summary(epw_summary_path)

    return SiteContext(
        svf_mean=round(svf, 3),
        canyon_hw_ratio=hw_ratio,
        canyon_wind_correction=wind_correction,
        surrounding_heights_m=nearby_heights,
        solar_obstruction_angles=obstruction,
        green_cover_ratio_50m=green_cover,
        thermal_comfort_gridcode=gridcode,
        thermal_comfort_label=comfort_label,
        july_diurnal_swing_C=epw["july_diurnal_swing_C"],
        summer_mean_temp_C=epw["summer_mean_temp_C"],
        summer_peak_temp_C=epw["summer_peak_temp_C"],
        summer_CDH_above_26C=epw["summer_CDH_above_26C"],
        dominant_wind_direction=epw["dominant_wind_direction"],
        summer_mean_wind_m_s=epw["summer_mean_wind_m_s"],
        night_purge_hours_below_22C=int(epw["night_purge_hours_below_22C"]),
        july_EN16798_upper_C=epw["july_EN16798_upper_C"],
        july_ASHRAE55_upper_C=epw["july_ASHRAE55_upper_C"],
        summer_mean_GHI_Wh_m2=epw["summer_mean_GHI_Wh_m2"],
        summer_peak_GHI_Wh_m2=epw["summer_peak_GHI_Wh_m2"],
    )
