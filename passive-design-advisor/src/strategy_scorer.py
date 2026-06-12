"""
Stage 4 — Strategy Scoring Model (MAUT)
Multi-Attribute Utility Theory scoring for 5 passive design strategies.
All factor weights are from published sensitivity analyses — do not change
without updating the reference citation.
"""

from dataclasses import dataclass, field

from src.context_enricher import SiteContext
from src.ifc_parser import BuildingFeatures, MASS_SCORE
from src.thermal_diagnosis import ThermalDiagnosis, get_cached_facade_ghi
from src.utils import linear_ramp, inverse_ramp

EPW_PATH = "data/ESP_CT_Barcelona-El.Prat.AP.081810_TMYx.epw"


# ── Data class ────────────────────────────────────────────────────────────────

@dataclass
class StrategyScore:
    strategy_name: str
    precondition_met: str        # "YES" / "PARTIAL" / "NO"
    precondition_reason: str
    impact_score: float          # 0–100
    impact_level: str            # "HIGH" / "MEDIUM" / "LOW"
    factor_scores: dict          # {factor: {"raw": x, "mu": y, "weighted": z}}
    affected_element_ids: list[str]
    key_driver: str


# ── Shared helpers ────────────────────────────────────────────────────────────

def score_to_level(score: float) -> str:
    """
    Map 0–100 impact score to level.
    Thresholds from Lapisa et al. 2018 Table 5:
    >40% ODH reduction → HIGH, 20–40% → MEDIUM, <20% → LOW.
    Mapped proportionally to 0–100 scale.
    """
    if score >= 66:
        return "HIGH"
    elif score >= 33:
        return "MEDIUM"
    else:
        return "LOW"


def _weighted_score(factors: dict) -> float:
    """Compute 0–100 MAUT score from factor dict."""
    numerator = sum(v["mu"] * v["w"] for v in factors.values())
    denominator = sum(v["w"] for v in factors.values())
    return round(100.0 * numerator / denominator, 1) if denominator > 0 else 0.0


def _key_driver(factors: dict) -> str:
    """Return name of factor with highest weighted contribution."""
    return max(factors, key=lambda k: factors[k]["mu"] * factors[k]["w"])


def _to_output(factors: dict) -> dict:
    """Convert internal factor dict to serialisable output format."""
    return {
        k: {"raw": v["raw"], "mu": round(v["mu"], 3), "weighted": round(v["mu"] * v["w"], 3)}
        for k, v in factors.items()
    }


def _dominant_mass(building: BuildingFeatures) -> str:
    if not building.facades:
        return "medium"
    counts: dict[str, int] = {}
    for f in building.facades:
        counts[f.construction_mass] = counts.get(f.construction_mass, 0) + 1
    return max(counts, key=counts.get)


# ── Strategy 1: External Shading ──────────────────────────────────────────────
#
# Weights: facade_GHI 0.40, WWR 0.31, orientation 0.29
# Source: Lapisa et al. 2018 Table 3; Szokolay 2004 §2.3

SHADING_ORIENTATION_MU: dict[str, float] = {
    "N": 0.00, "NE": 0.20, "E": 0.50,
    "SE": 0.75, "S": 0.85, "SW": 1.00,
    "W": 0.75, "NW": 0.30,
}


def score_shading(
    building: BuildingFeatures,
    context: SiteContext,
    epw_path: str = EPW_PATH,
) -> StrategyScore:
    """
    Score external shading for the facade with highest potential benefit.
    Source: Santamouris & Asimakopoulos 1996 §4.2; Lapisa et al. 2018 Table 3.
    """
    best_score = -1.0
    best_factors = {}
    best_facade = None
    best_precondition = "NO"
    best_reason = ""
    best_elements: list[str] = []

    for facade in building.facades:
        ghi = get_cached_facade_ghi(
            facade.orientation_label,
            building.site_latitude,
            building.site_longitude,
            epw_path,
        )

        # Precondition (Santamouris 1996 §4.2)
        if ghi > 150 and facade.wwr > 0.15 and facade.orientation_label not in ("N", "NE"):
            precondition = "YES"
            reason = (
                f"{facade.orientation_label} facade GHI = {ghi:.0f} Wh/m² > 150 threshold. "
                f"WWR = {facade.wwr:.2f}."
            )
        elif ghi > 100 or facade.wwr > 0.10:
            precondition = "PARTIAL"
            reason = (
                f"Partial: GHI = {ghi:.0f} Wh/m², WWR = {facade.wwr:.2f} — "
                "below primary threshold but shading may still reduce gains."
            )
        else:
            precondition = "NO"
            reason = f"GHI = {ghi:.0f} Wh/m² and WWR = {facade.wwr:.2f} too low to justify shading."

        if precondition == "NO":
            continue

        factors = {
            "facade_GHI":  {"raw": round(ghi, 1),        "mu": linear_ramp(ghi, 100, 350),              "w": 0.40},
            "WWR":         {"raw": round(facade.wwr, 3), "mu": linear_ramp(facade.wwr, 0.10, 0.50),     "w": 0.31},
            "orientation": {"raw": facade.orientation_label,
                            "mu": SHADING_ORIENTATION_MU[facade.orientation_label],                      "w": 0.29},
        }
        score = _weighted_score(factors)

        if score > best_score:
            best_score = score
            best_factors = factors
            best_facade = facade
            best_precondition = precondition
            best_reason = reason
            best_elements = [facade.element_id] + facade.window_element_ids

    if best_facade is None:
        # All facades failed precondition
        return StrategyScore(
            strategy_name="shading",
            precondition_met="NO",
            precondition_reason="No facade meets minimum GHI/WWR thresholds for shading.",
            impact_score=0.0,
            impact_level="LOW",
            factor_scores={},
            affected_element_ids=[],
            key_driver="",
        )

    return StrategyScore(
        strategy_name="shading",
        precondition_met=best_precondition,
        precondition_reason=best_reason,
        impact_score=best_score,
        impact_level=score_to_level(best_score),
        factor_scores=_to_output(best_factors),
        affected_element_ids=best_elements,
        key_driver=_key_driver(best_factors),
    )


# ── Strategy 2: Cross-Ventilation ─────────────────────────────────────────────
#
# Weights: v_canyon 0.35, D/H 0.30, inlet_ratio 0.20, opposing_outlet 0.15
# Source: Santamouris 1996 Table 8.3; CIBSE AM10:2005 §3.4

def score_cross_ventilation(
    building: BuildingFeatures,
    context: SiteContext,
) -> StrategyScore:
    """
    Source: CIBSE AM10:2005 §3.4; Santamouris 1996; Givoni 1994 Ch.3; Blocken 2007.
    """
    v_canyon = context.summer_mean_wind_m_s * context.canyon_wind_correction
    dh_ratio = (
        building.building_depth_m / building.floor_to_ceiling_height_m
        if building.floor_to_ceiling_height_m > 0 else 99.0
    )
    inlet_ratio = (
        building.operable_window_area_m2 / building.total_floor_area_m2
        if building.total_floor_area_m2 > 0 else 0.0
    )
    has_opposing = 1.0 if building.has_opposing_openings else 0.0

    # Precondition (CIBSE AM10:2005 §3.4)
    if building.has_opposing_openings and dh_ratio <= 5.0 and v_canyon >= 0.5:
        precondition = "YES"
        reason = (
            f"Opposing openings present, D/H = {dh_ratio:.1f} ≤ 5.0, "
            f"canyon wind = {v_canyon:.1f} m/s ≥ 0.5 m/s."
        )
    elif dh_ratio > 5.0:
        precondition = "NO"
        reason = (
            f"D/H = {dh_ratio:.1f} > 5.0 — cross-ventilation physically impossible "
            "(CIBSE AM10:2005 §3.4)."
        )
    else:
        precondition = "PARTIAL"
        if not building.has_opposing_openings:
            reason = (
                f"No opposing openings — openings could be added. D/H = {dh_ratio:.1f} ≤ 5.0."
            )
        else:
            reason = (
                f"Opposing openings present but canyon wind = {v_canyon:.1f} m/s < 0.5 m/s."
            )

    factors = {
        "v_canyon":       {"raw": round(v_canyon, 2),   "mu": linear_ramp(v_canyon, 0.5, 3.5),   "w": 0.35},
        "DH_ratio":       {"raw": round(dh_ratio, 2),   "mu": inverse_ramp(dh_ratio, 2.0, 5.0),  "w": 0.30},
        "inlet_ratio":    {"raw": round(inlet_ratio, 4),"mu": linear_ramp(inlet_ratio, 0.02, 0.10), "w": 0.20},
        "opposing_outlet":{"raw": bool(building.has_opposing_openings), "mu": has_opposing,        "w": 0.15},
    }
    score = _weighted_score(factors) if precondition != "NO" else 0.0

    # Affected elements: walls lacking openings (if PARTIAL) + all windows
    affected = []
    for f in building.facades:
        if f.window_area_m2 == 0:
            affected.append(f.element_id)
        affected.extend(f.window_element_ids)

    return StrategyScore(
        strategy_name="cross_ventilation",
        precondition_met=precondition,
        precondition_reason=reason,
        impact_score=score,
        impact_level=score_to_level(score),
        factor_scores=_to_output(factors),
        affected_element_ids=affected,
        key_driver=_key_driver(factors) if precondition != "NO" else "",
    )


# ── Strategy 3: Thermal Mass ──────────────────────────────────────────────────
#
# Weights: diurnal_swing 0.40, mass_score 0.35, IHG_proxy 0.25
# Source: Balaras 1996; Givoni 1994 Ch.6; ISO 13786:2017; EN ISO 52016-1:2017

IHG_PROXY: dict[str, float] = {
    "residential": 0.35,
    "office":      0.65,
    "mixed":       0.50,
}


def score_thermal_mass(
    building: BuildingFeatures,
    context: SiteContext,
) -> StrategyScore:
    """
    Source: Balaras 1996 Energy and Buildings 24(3):179–195;
    Givoni 1994 Ch.6; ISO 13786:2017; EN ISO 52016-1:2017 §B.4.

    NOTE: Barcelona July diurnal swing ≈ 6.54°C — PARTIAL range.
    This is a correct result for the Mediterranean coastal climate.
    """
    dom_mass = _dominant_mass(building)
    mass_score_val = MASS_SCORE[dom_mass]
    delta_t = context.july_diurnal_swing_C
    ihg = IHG_PROXY.get(building.building_use, 0.50)

    # Precondition (Givoni 1994 Ch.6)
    if dom_mass == "heavy" or (dom_mass == "medium" and delta_t > 6.0):
        precondition = "YES"
        reason = f"Construction mass = {dom_mass}, diurnal swing = {delta_t:.1f}°C."
    elif dom_mass == "medium" or (dom_mass == "lightweight" and delta_t > 8.0):
        precondition = "PARTIAL"
        reason = (
            f"Construction mass = {dom_mass}, diurnal swing = {delta_t:.1f}°C. "
            "Moderate effectiveness expected."
        )
    else:
        precondition = "NO"
        reason = (
            f"Lightweight construction with diurnal swing = {delta_t:.1f}°C < 6°C — "
            "thermal mass cannot be cost-effectively retrofitted (Givoni 1994 Ch.6)."
        )

    factors = {
        "diurnal_swing": {"raw": round(delta_t, 2), "mu": linear_ramp(delta_t, 5.0, 15.0), "w": 0.40},
        "mass_score":    {"raw": dom_mass,           "mu": mass_score_val,                   "w": 0.35},
        "IHG_proxy":     {"raw": building.building_use, "mu": ihg,                           "w": 0.25},
    }
    score = _weighted_score(factors) if precondition != "NO" else 0.0

    # Affected: walls and slabs with lightweight/medium mass
    affected = [
        f.element_id for f in building.facades
        if f.construction_mass in ("lightweight", "medium")
    ]
    if building.roof and building.roof.construction_mass in ("lightweight", "medium"):
        affected.append(building.roof.element_id)

    return StrategyScore(
        strategy_name="thermal_mass",
        precondition_met=precondition,
        precondition_reason=reason,
        impact_score=score,
        impact_level=score_to_level(score),
        factor_scores=_to_output(factors),
        affected_element_ids=affected,
        key_driver=_key_driver(factors) if precondition != "NO" else "",
    )


# ── Strategy 4: Night Purge Ventilation ───────────────────────────────────────
#
# Weights: hours_below_22C 0.45, A_op/A_floor 0.30, mass_score 0.25
# Source: Santamouris 1996 §9.3; CIBSE TM52:2013 §4.2; Balaras 1996

def score_night_purge(
    building: BuildingFeatures,
    context: SiteContext,
) -> StrategyScore:
    """
    Source: Santamouris 1996 §9.3; CIBSE TM52:2013 §4.2; Balaras 1996.

    NOTE: the Barcelona TMYx EPW summary reports 469 summer night hours below
    22°C (outputs/epw_summary.json), comfortably above the 150 h "YES"
    threshold — operable-window ratio and thermal mass are then the score
    drivers. Do not adjust thresholds to inflate or deflate this score.
    """
    hours = context.night_purge_hours_below_22C
    op_ratio = (
        building.operable_window_area_m2 / building.total_floor_area_m2
        if building.total_floor_area_m2 > 0 else 0.0
    )
    dom_mass = _dominant_mass(building)
    mass_val = MASS_SCORE[dom_mass]

    # Precondition (Santamouris 1996 §9.3)
    if hours >= 150 and op_ratio >= 0.05:
        precondition = "YES"
        reason = f"{hours} night hours below 22°C, operable ratio = {op_ratio:.3f}."
    elif hours < 50:
        precondition = "NO"
        reason = (
            f"Only {hours} summer night hours below 22°C — insufficient for effective "
            "night cooling (Santamouris 1996 §9.3 requires ≥50 h)."
        )
    else:
        precondition = "PARTIAL"
        if hours < 150:
            reason = f"{hours} night hours below 22°C — limited by Barcelona's coastal climate."
        else:
            reason = f"Operable window ratio = {op_ratio:.3f} — below 5% floor area target."

    factors = {
        "hours_below_22C": {"raw": hours,               "mu": linear_ramp(hours, 50, 300),       "w": 0.45},
        "op_ratio":        {"raw": round(op_ratio, 4),  "mu": linear_ramp(op_ratio, 0.02, 0.10), "w": 0.30},
        "mass_score":      {"raw": dom_mass,             "mu": mass_val,                           "w": 0.25},
    }
    score = _weighted_score(factors) if precondition != "NO" else 0.0

    # Affected: fixed windows
    affected = []
    for f in building.facades:
        affected.extend(f.window_element_ids)

    return StrategyScore(
        strategy_name="night_purge",
        precondition_met=precondition,
        precondition_reason=reason,
        impact_score=score,
        impact_level=score_to_level(score),
        factor_scores=_to_output(factors),
        affected_element_ids=affected,
        key_driver=_key_driver(factors) if precondition != "NO" else "",
    )


# ── Strategy 5: Green Roof ────────────────────────────────────────────────────
#
# Weights: svf_roof 0.40, gridcode 0.35, roof_ratio 0.25
# Source: Santamouris 2014; Getter & Rowe 2006

def score_green_roof(
    building: BuildingFeatures,
    context: SiteContext,
) -> StrategyScore:
    """
    Source: Santamouris 2014 Solar Energy 103:682–703;
    Getter & Rowe 2006 Landscape Urban Plan. 77(3):217–229.
    """
    roof = building.roof
    svf_roof = context.svf_mean
    gridcode = context.thermal_comfort_gridcode
    roof_ratio = (
        roof.area_m2 / building.total_floor_area_m2
        if building.total_floor_area_m2 > 0 else 0.0
    )

    # Precondition (Santamouris 2014)
    if not roof.is_exposed or svf_roof < 0.2:
        precondition = "NO"
        reason = (
            "Roof is not exposed" if not roof.is_exposed
            else f"Roof SVF = {svf_roof:.2f} < 0.2 — insufficient solar access for evapotranspiration."
        )
    elif roof.is_exposed and roof_ratio >= 0.3:
        precondition = "YES"
        reason = (
            f"Exposed roof, area ratio = {roof_ratio:.2f} ≥ 0.3, SVF = {svf_roof:.2f}."
        )
    else:
        precondition = "PARTIAL"
        reason = (
            f"Exposed roof but area ratio = {roof_ratio:.2f} < 0.3 — partial coverage."
        )

    # gridcode → mu: (gridcode - 1) / 5 so gridcode 6 (worst comfort) → mu = 1.0
    gridcode_mu = (gridcode - 1) / 5.0

    factors = {
        "svf_roof":   {"raw": round(svf_roof, 3),  "mu": linear_ramp(svf_roof, 0.2, 1.0),  "w": 0.40},
        "gridcode":   {"raw": gridcode,             "mu": round(gridcode_mu, 3),              "w": 0.35},
        "roof_ratio": {"raw": round(roof_ratio, 3), "mu": linear_ramp(roof_ratio, 0.1, 0.5), "w": 0.25},
    }
    score = _weighted_score(factors) if precondition != "NO" else 0.0

    return StrategyScore(
        strategy_name="green_roof",
        precondition_met=precondition,
        precondition_reason=reason,
        impact_score=score,
        impact_level=score_to_level(score),
        factor_scores=_to_output(factors),
        affected_element_ids=[roof.element_id],
        key_driver=_key_driver(factors) if precondition != "NO" else "",
    )


# ── Ranking ───────────────────────────────────────────────────────────────────

def rank_strategies(scores: list[StrategyScore]) -> list[StrategyScore]:
    """
    Rank strategies by impact_score descending.
    Strategies with precondition_met="NO" are excluded from recommendations
    but included in the report with explanation.
    Higher score = more ODH reduction = higher implementation priority.
    """
    viable   = [s for s in scores if s.precondition_met != "NO"]
    excluded = [s for s in scores if s.precondition_met == "NO"]
    viable.sort(key=lambda s: s.impact_score, reverse=True)
    return viable + excluded


# ── Main scoring entry point ──────────────────────────────────────────────────

def score_all_strategies(
    building: BuildingFeatures,
    context: SiteContext,
    epw_path: str = EPW_PATH,
) -> list[StrategyScore]:
    """
    Score all 5 strategies and return ranked list.
    """
    scores = [
        score_shading(building, context, epw_path),
        score_cross_ventilation(building, context),
        score_thermal_mass(building, context),
        score_night_purge(building, context),
        score_green_roof(building, context),
    ]
    return rank_strategies(scores)
