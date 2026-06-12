"""
Stage 3 — Simplified Thermal Diagnosis
Computes a proxy estimate of Overheating Degree Hours (ODH) and identifies
which building elements are the primary contributors to overheating risk.

This is a physics-based proxy model, NOT a full thermal simulation.
Justified by EN 16798-1:2019 Annex F simplified calculation methods.
"""

from dataclasses import dataclass

import pandas as pd
import pvlib

from src.context_enricher import SiteContext
from src.ifc_parser import BuildingFeatures, FacadeFeature
from src.utils import linear_ramp, resolve_path

# ── Orientation weights at Barcelona lat 41°N ─────────────────────────────────
# Peak afternoon solar 14:00–18:00 July; SW and W prioritised.
# Source: Szokolay 2004 §2.3 + pvlib sun path at lat 41.3°N
ORIENTATION_WEIGHTS: dict[str, float] = {
    "N": 0.10, "NE": 0.30, "E": 0.55,
    "SE": 0.75, "S": 0.85, "SW": 0.95,
    "W": 0.75, "NW": 0.35,
}

ORIENTATION_TO_AZIMUTH: dict[str, int] = {
    "N": 0, "NE": 45, "E": 90, "SE": 135,
    "S": 180, "SW": 225, "W": 270, "NW": 315,
}

# EN 16798-1:2019 minimum effective ventilation threshold (Annex B, Table B.3)
VENTILATION_THRESHOLD = 0.05   # 5% of floor area

# Default clear glass SHGC — EN 410:2011 Table 2
DEFAULT_SHGC = 0.6

EPW_PATH = "data/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw"


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class FacadeThermalStress:
    element_id: str
    orientation_label: str
    solar_heat_gain_index: float      # normalised 0–1
    ventilation_cooling_index: float  # normalised 0–1
    net_thermal_stress: float         # SHGI - VCI, proxy for ODH contribution
    is_critical: bool


@dataclass
class ThermalDiagnosis:
    estimated_proxy_ODH: float
    critical_facades: list[str]
    ventilation_deficit: bool
    night_purge_viable: bool
    thermal_mass_deficit: bool
    overheating_risk_level: str
    diagnosis_text: str


# ── pvlib facade irradiance ───────────────────────────────────────────────────

def get_facade_summer_ghi(
    orientation_label: str,
    site_lat: float,
    site_lon: float,
    epw_path: str = EPW_PATH,
) -> float:
    """
    Mean summer (JJA) plane-of-array irradiance (Wh/m²) for a vertical facade.
    Uses pvlib Perez transposition model.

    Source: Perez R. et al. 1990, Solar Energy 44(5):271–289.
    """
    df, _ = pvlib.iotools.read_epw(str(resolve_path(epw_path)), coerce_year=2001)
    df.index = pd.date_range(
        start="2001-01-01 00:00",
        periods=8760,
        freq="h",
        tz="Etc/GMT-1",
    )
    summer = df[df.index.month.isin([6, 7, 8])]

    location = pvlib.location.Location(
        latitude=site_lat,
        longitude=site_lon,
        tz="Etc/GMT-1",
    )
    solar_pos = location.get_solarposition(summer.index)
    dni_extra = pvlib.irradiance.get_extra_radiation(summer.index)

    poa = pvlib.irradiance.get_total_irradiance(
        surface_tilt=90,
        surface_azimuth=ORIENTATION_TO_AZIMUTH[orientation_label],
        solar_zenith=solar_pos["apparent_zenith"],
        solar_azimuth=solar_pos["azimuth"],
        dni=summer["dni"],
        ghi=summer["ghi"],
        dhi=summer["dhi"],
        dni_extra=dni_extra,
        model="perez",
    )
    return float(poa["poa_global"].mean())


# Cache GHI per orientation to avoid repeated EPW reads
_ghi_cache: dict[str, float] = {}


def get_cached_facade_ghi(
    orientation_label: str,
    site_lat: float,
    site_lon: float,
    epw_path: str = EPW_PATH,
) -> float:
    key = f"{orientation_label}_{site_lat:.4f}_{site_lon:.4f}"
    if key not in _ghi_cache:
        _ghi_cache[key] = get_facade_summer_ghi(orientation_label, site_lat, site_lon, epw_path)
    return _ghi_cache[key]


# ── Solar heat gain index ─────────────────────────────────────────────────────

def compute_shgi(
    facade: FacadeFeature,
    site_lat: float,
    site_lon: float,
    shgc: float = DEFAULT_SHGC,
    epw_path: str = EPW_PATH,
) -> float:
    """
    SHGI_i = GHI_facade × WWR × SHGC × shading_factor × orientation_weight

    shading_factor is the solar transmission of the facade's shading state
    (1.0 = unshaded → full gain, 0.3 = heavily shaded → 30% of gain).
    Returns raw (unnormalised) value.
    """
    ghi = get_cached_facade_ghi(facade.orientation_label, site_lat, site_lon, epw_path)
    ow = ORIENTATION_WEIGHTS[facade.orientation_label]
    return ghi * facade.wwr * shgc * facade.shading_factor * ow


# ── Ventilation cooling index ─────────────────────────────────────────────────

def compute_vci(
    facade: FacadeFeature,
    building: BuildingFeatures,
    context: SiteContext,
) -> float:
    """
    VCI = min(1, (v_canyon × A_inlet / A_floor) / threshold)

    Source: EN 16798-1:2019 Annex B, Table B.3.
    """
    v_canyon = context.summer_mean_wind_m_s * context.canyon_wind_correction
    if building.total_floor_area_m2 < 1.0:
        return 0.0
    inlet_ratio = facade.window_area_m2 / building.total_floor_area_m2
    vci = (v_canyon * inlet_ratio) / VENTILATION_THRESHOLD
    return float(min(1.0, vci))


# ── Risk classification ───────────────────────────────────────────────────────

def classify_risk(proxy_odh: float) -> str:
    """
    Classify overheating risk from proxy ODH.
    Thresholds calibrated to EN 16798-1:2019 Category II limit of 100 ODH (§6.3.4.2).
    Proxy ODH scaled to approximate ODH equivalence via Evola et al. 2017
    calibration for Mediterranean apartments.
    """
    if proxy_odh < 0.15:
        return "LOW"
    elif proxy_odh < 0.35:
        return "MEDIUM"
    elif proxy_odh < 0.60:
        return "HIGH"
    else:
        return "CRITICAL"


def build_diagnosis_text(
    risk_level: str,
    proxy_odh: float,
    critical_facades: list[str],
    ventilation_deficit: bool,
    night_purge_viable: bool,
    thermal_mass_deficit: bool,
    building: BuildingFeatures,
    context: SiteContext,
) -> str:
    parts = [
        f"The building shows {risk_level} overheating risk (proxy ODH = {proxy_odh:.2f}). "
    ]

    if critical_facades:
        parts.append(
            f"Critical facades driving heat gain: {', '.join(critical_facades[:3])}. "
        )

    if ventilation_deficit:
        parts.append(
            "Ventilation is insufficient to offset solar gains — "
            f"operable window area ({building.operable_window_area_m2:.1f} m²) "
            f"is below 5% of floor area threshold. "
        )
    else:
        parts.append("Ventilation capacity is adequate relative to solar gains. ")

    if night_purge_viable:
        parts.append(
            f"Night purge is viable: {context.night_purge_hours_below_22C} hours "
            "below 22°C available in summer nights. "
        )
    else:
        parts.append(
            f"Night purge has limited effectiveness: only {context.night_purge_hours_below_22C} "
            "summer night hours below 22°C — Barcelona's coastal climate constrains this strategy. "
        )

    if thermal_mass_deficit:
        parts.append(
            f"Thermal mass is insufficient — lightweight construction with "
            f"{context.july_diurnal_swing_C:.1f}°C diurnal swing provides minimal buffering. "
        )

    return "".join(parts)


# ── Main diagnosis function ───────────────────────────────────────────────────

def diagnose(
    building: BuildingFeatures,
    context: SiteContext,
    shgc: float = DEFAULT_SHGC,
    epw_path: str = EPW_PATH,
) -> ThermalDiagnosis:
    """
    Compute proxy ODH and overheating diagnosis for the building.
    Returns a ThermalDiagnosis dataclass.
    """
    if not building.facades:
        # Should not reach here — ifc_parser synthesises fallback facades.
        # Return a safe zero-stress diagnosis rather than crashing.
        return ThermalDiagnosis(
            estimated_proxy_ODH=0.0,
            critical_facades=[],
            ventilation_deficit=True,
            night_purge_viable=context.night_purge_hours_below_22C >= 75,
            thermal_mass_deficit=False,
            overheating_risk_level="LOW",
            diagnosis_text="No facade data available — results are indicative only.",
        )

    # Compute raw SHGI and VCI for each facade
    raw_shgi: list[float] = []
    raw_vci:  list[float] = []

    for facade in building.facades:
        raw_shgi.append(compute_shgi(facade, building.site_latitude, building.site_longitude, shgc, epw_path))
        raw_vci.append(compute_vci(facade, building, context))

    # Normalise SHGI to [0,1]
    max_shgi = max(raw_shgi) if max(raw_shgi) > 0 else 1.0
    norm_shgi = [v / max_shgi for v in raw_shgi]

    facade_stresses: list[FacadeThermalStress] = []
    for i, facade in enumerate(building.facades):
        net_stress = max(0.0, norm_shgi[i] - raw_vci[i])
        facade_stresses.append(FacadeThermalStress(
            element_id=facade.element_id,
            orientation_label=facade.orientation_label,
            solar_heat_gain_index=round(norm_shgi[i], 3),
            ventilation_cooling_index=round(raw_vci[i], 3),
            net_thermal_stress=round(net_stress, 3),
            is_critical=False,
        ))

    # Mark up to 2 facades as critical — only if they carry real thermal stress.
    # (Previously the top-2 were always flagged, producing "critical facades"
    # in buildings with zero overheating risk.)
    CRITICAL_STRESS_MIN = 0.05
    sorted_by_stress = sorted(facade_stresses, key=lambda f: f.net_thermal_stress, reverse=True)
    for fs in sorted_by_stress[:2]:
        if fs.net_thermal_stress > CRITICAL_STRESS_MIN:
            fs.is_critical = True

    # Area-weighted mean stress (0–1). A plain sum would scale with the number
    # of wall segments in the model, making risk depend on modelling style.
    facade_areas = [f.gross_area_m2 for f in building.facades]
    total_facade_area = sum(facade_areas) or 1.0
    proxy_odh = round(
        sum(fs.net_thermal_stress * a for fs, a in zip(facade_stresses, facade_areas))
        / total_facade_area,
        3,
    )
    risk_level = classify_risk(proxy_odh)
    critical_ids = [f.element_id for f in facade_stresses if f.is_critical]

    # Ventilation deficit: total operable area < 5% of floor area
    ventilation_deficit = (
        building.operable_window_area_m2 < VENTILATION_THRESHOLD * building.total_floor_area_m2
    )

    # Night purge viability
    night_purge_viable = context.night_purge_hours_below_22C >= 75

    # Thermal mass deficit: lightweight construction with low diurnal swing
    dominant_mass = _dominant_construction_mass(building)
    thermal_mass_deficit = (
        dominant_mass == "lightweight" and context.july_diurnal_swing_C < 6.0
    )

    diagnosis_text = build_diagnosis_text(
        risk_level, proxy_odh, critical_ids,
        ventilation_deficit, night_purge_viable, thermal_mass_deficit,
        building, context,
    )

    return ThermalDiagnosis(
        estimated_proxy_ODH=proxy_odh,
        critical_facades=critical_ids,
        ventilation_deficit=ventilation_deficit,
        night_purge_viable=night_purge_viable,
        thermal_mass_deficit=thermal_mass_deficit,
        overheating_risk_level=risk_level,
        diagnosis_text=diagnosis_text,
    )


def _dominant_construction_mass(building: BuildingFeatures) -> str:
    """Return the most common construction mass category across all facades."""
    if not building.facades:
        return "medium"
    counts = {"lightweight": 0, "medium": 0, "heavy": 0}
    for f in building.facades:
        counts[f.construction_mass] = counts.get(f.construction_mass, 0) + 1
    return max(counts, key=counts.get)
