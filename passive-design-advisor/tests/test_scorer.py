"""
Unit tests for strategy scoring model.
Run from project root:
    python -m pytest tests/test_scorer.py -v
"""

import pytest

from src.utils import linear_ramp, inverse_ramp
from src.ifc_parser import (
    FacadeFeature, RoofFeature, BuildingFeatures, MASS_SCORE, degrees_to_label,
)
from src.context_enricher import SiteContext
from src.strategy_scorer import (
    score_shading,
    score_cross_ventilation,
    score_thermal_mass,
    score_night_purge,
    score_green_roof,
    score_to_level,
    rank_strategies,
    StrategyScore,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_context(**overrides) -> SiteContext:
    defaults = dict(
        svf_mean=0.7,
        canyon_hw_ratio=0.8,
        canyon_wind_correction=0.7,
        surrounding_heights_m=[12.0, 15.0, 10.0],
        solar_obstruction_angles={"S": 10.0, "N": 5.0},
        green_cover_ratio_50m=0.1,
        thermal_comfort_gridcode=5,
        thermal_comfort_label="Low",
        july_diurnal_swing_C=6.54,
        summer_mean_temp_C=24.5,
        summer_peak_temp_C=36.2,
        summer_CDH_above_26C=850.0,
        dominant_wind_direction="NE",
        summer_mean_wind_m_s=3.2,
        night_purge_hours_below_22C=104,
        july_EN16798_upper_C=27.5,
        july_ASHRAE55_upper_C=28.1,
        summer_mean_GHI_Wh_m2=310.0,
        summer_peak_GHI_Wh_m2=950.0,
    )
    defaults.update(overrides)
    return SiteContext(**defaults)


def make_facade(**overrides) -> FacadeFeature:
    defaults = dict(
        element_id="wall_001",
        orientation_deg=180.0,
        orientation_label="S",
        gross_area_m2=45.0,
        window_area_m2=17.0,
        wwr=0.38,
        window_element_ids=["win_001", "win_002"],
        u_value=1.2,
        construction_mass="medium",
        shading_factor=1.0,
        is_exterior=True,
    )
    defaults.update(overrides)
    return FacadeFeature(**defaults)


def make_building(**overrides) -> BuildingFeatures:
    facade_s  = make_facade(orientation_label="S",  orientation_deg=180.0, wwr=0.38)
    facade_sw = make_facade(element_id="wall_002", orientation_label="SW", orientation_deg=225.0, wwr=0.30)
    facade_n  = make_facade(element_id="wall_003", orientation_label="N",  orientation_deg=0.0,   wwr=0.10,
                             window_element_ids=["win_003"])
    roof = RoofFeature(
        element_id="roof_001",
        area_m2=150.0,
        is_exposed=True,
        inclination_deg=0.0,
        u_value=0.25,
        construction_mass="medium",
    )
    defaults = dict(
        ifc_file_path="test_building.ifc",
        site_latitude=41.3851,
        site_longitude=2.1734,
        building_use="residential",
        total_floor_area_m2=450.0,
        floor_to_ceiling_height_m=2.8,
        building_depth_m=14.0,
        building_width_m=9.0,
        number_of_floors=3,
        facades=[facade_s, facade_sw, facade_n],
        roof=roof,
        has_opposing_openings=True,
        operable_window_area_m2=18.0,
    )
    defaults.update(overrides)
    return BuildingFeatures(**defaults)


# ── linear_ramp tests ─────────────────────────────────────────────────────────

def test_linear_ramp_below_min():
    assert linear_ramp(50, 100, 300) == 0.0


def test_linear_ramp_above_max():
    assert linear_ramp(400, 100, 300) == 1.0


def test_linear_ramp_midpoint():
    assert linear_ramp(200, 100, 300) == pytest.approx(0.5)


def test_inverse_ramp():
    assert inverse_ramp(2.0, 2.0, 5.0) == pytest.approx(1.0)
    assert inverse_ramp(5.0, 2.0, 5.0) == pytest.approx(0.0)
    assert inverse_ramp(3.5, 2.0, 5.0) == pytest.approx(0.5)


# ── degrees_to_label tests ────────────────────────────────────────────────────

def test_degrees_to_label_north():
    assert degrees_to_label(0) == "N"
    assert degrees_to_label(355) == "N"


def test_degrees_to_label_cardinal():
    assert degrees_to_label(90) == "E"
    assert degrees_to_label(180) == "S"
    assert degrees_to_label(270) == "W"


def test_degrees_to_label_southeast():
    assert degrees_to_label(135) == "SE"


# ── score_to_level tests ──────────────────────────────────────────────────────

def test_score_to_level_high():
    assert score_to_level(80) == "HIGH"
    assert score_to_level(66) == "HIGH"


def test_score_to_level_medium():
    assert score_to_level(50) == "MEDIUM"
    assert score_to_level(33) == "MEDIUM"


def test_score_to_level_low():
    assert score_to_level(20) == "LOW"
    assert score_to_level(0) == "LOW"


# ── Night purge: Barcelona should score LOW ───────────────────────────────────

def test_night_purge_low_barcelona():
    """
    Barcelona's 104 summer night hours below 22°C → LOW night purge score.
    linear_ramp(104, 50, 300) = 0.216
    Expected score < 33.
    """
    building = make_building()
    context  = make_context(night_purge_hours_below_22C=104)
    result   = score_night_purge(building, context)
    assert result.impact_score < 33, (
        f"Night purge score {result.impact_score:.1f} should be LOW (<33) for Barcelona climate"
    )
    assert result.impact_level == "LOW"


def test_night_purge_precondition_no_when_below_50():
    """Fewer than 50 cooling hours → precondition NO."""
    building = make_building()
    context  = make_context(night_purge_hours_below_22C=40)
    result   = score_night_purge(building, context)
    assert result.precondition_met == "NO"
    assert result.impact_score == 0.0


# ── Cross-ventilation: deep plan → NO ────────────────────────────────────────

def test_precondition_cross_vent_deep_plan():
    """
    D/H > 5.0 → precondition NO.
    building_depth = 18m, floor_height = 2.8m → D/H = 6.43.
    """
    building = make_building(building_depth_m=18.0, floor_to_ceiling_height_m=2.8)
    context  = make_context()
    result   = score_cross_ventilation(building, context)
    assert result.precondition_met == "NO"
    assert result.impact_score == 0.0


def test_cross_vent_feasible():
    """D/H ≤ 5.0 with opposing openings and adequate wind → YES or PARTIAL."""
    building = make_building(building_depth_m=10.0, floor_to_ceiling_height_m=2.8)
    context  = make_context(summer_mean_wind_m_s=3.2, canyon_wind_correction=0.7)
    result   = score_cross_ventilation(building, context)
    assert result.precondition_met in ("YES", "PARTIAL")
    assert result.impact_score > 0


# ── SVF: open site → 1.0 is handled in context_enricher (unit tested separately) ─

# ── Thermal comfort zone ──────────────────────────────────────────────────────

def test_thermal_mass_lightweight_low_swing():
    """Lightweight construction + low diurnal swing → precondition NO."""
    building = make_building()
    for f in building.facades:
        f.construction_mass = "lightweight"
    context = make_context(july_diurnal_swing_C=4.0)
    result  = score_thermal_mass(building, context)
    assert result.precondition_met == "NO"
    assert result.impact_score == 0.0


def test_thermal_mass_heavy():
    """Heavy construction → precondition YES, score > 0."""
    building = make_building()
    for f in building.facades:
        f.construction_mass = "heavy"
    context = make_context(july_diurnal_swing_C=6.54)
    result  = score_thermal_mass(building, context)
    assert result.precondition_met == "YES"
    assert result.impact_score > 0


# ── Green roof ────────────────────────────────────────────────────────────────

def test_green_roof_not_exposed():
    """Non-exposed roof → precondition NO."""
    building = make_building()
    building.roof.is_exposed = False
    context  = make_context()
    result   = score_green_roof(building, context)
    assert result.precondition_met == "NO"
    assert result.impact_score == 0.0


def test_green_roof_high_svf():
    """Exposed roof, good SVF, worst comfort zone → higher score."""
    building = make_building()
    context  = make_context(svf_mean=0.85, thermal_comfort_gridcode=6)
    result   = score_green_roof(building, context)
    assert result.precondition_met in ("YES", "PARTIAL")
    assert result.impact_score > 0


# ── Ranking ───────────────────────────────────────────────────────────────────

def test_rank_strategies_no_excluded_last():
    """Strategies with precondition NO must appear after viable ones."""
    scores = [
        StrategyScore("a", "NO",      "reason", 80.0, "HIGH",   {}, [], ""),
        StrategyScore("b", "YES",     "reason", 60.0, "MEDIUM", {}, [], ""),
        StrategyScore("c", "PARTIAL", "reason", 70.0, "HIGH",   {}, [], ""),
    ]
    ranked = rank_strategies(scores)
    assert ranked[0].strategy_name == "c"
    assert ranked[1].strategy_name == "b"
    assert ranked[-1].strategy_name == "a"
    assert ranked[-1].precondition_met == "NO"
