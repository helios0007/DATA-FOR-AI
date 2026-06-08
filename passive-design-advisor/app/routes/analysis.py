"""
/api/analysis — Run the full pipeline (Stages 2–5) for a session.
Accepts site coordinates, rotation offset, and building use.
Returns scored strategies + thermal diagnosis.
"""

import json
from copy import deepcopy

from fastapi import APIRouter, HTTPException

from app.models import (
    AnalysisRequest, AnalysisResponse,
    DiagnosisResult, SiteResult, StrategyResult,
)
from app.session import session_store
from src.context_enricher import enrich
from src.ifc_parser import BuildingFeatures
from src.recommender import generate_report
from src.strategy_scorer import score_all_strategies
from src.thermal_diagnosis import diagnose

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _apply_rotation(building: BuildingFeatures, offset_deg: float) -> BuildingFeatures:
    """
    Return a copy of BuildingFeatures with all facade orientations
    rotated by offset_deg. Used when the user rotates the building in the UI.
    """
    if offset_deg == 0.0:
        return building

    from src.ifc_parser import degrees_to_label
    rotated = deepcopy(building)
    for facade in rotated.facades:
        new_deg = (facade.orientation_deg + offset_deg) % 360
        facade.orientation_deg = round(new_deg, 1)
        facade.orientation_label = degrees_to_label(new_deg)
    return rotated


@router.post("/run", response_model=AnalysisResponse)
async def run_analysis(req: AnalysisRequest):
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Upload an IFC file first.")

    building: BuildingFeatures = session["building"]

    # Apply user rotation and update site coordinates
    building = deepcopy(building)
    building.site_latitude  = req.site_lat
    building.site_longitude = req.site_lon
    building.building_use   = req.building_use
    building = _apply_rotation(building, req.rotation_offset_deg)

    # Stage 2
    try:
        context = enrich(
            req.site_lat, req.site_lon,
            building_height_m=building.number_of_floors * building.floor_to_ceiling_height_m,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Context enrichment failed: {e}")

    # Stage 3
    try:
        diagnosis = diagnose(building, context, shgc=req.shgc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Thermal diagnosis failed: {e}")

    # Stage 4
    ranked_scores = score_all_strategies(building, context)

    # Stage 5 (optional)
    try:
        report = generate_report(building, context, diagnosis, ranked_scores, skip_llm=req.skip_llm)
        session["report"] = report
        session["context"] = context
        session["diagnosis"] = diagnosis
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recommendation generation failed: {e}")

    return AnalysisResponse(
        session_id=req.session_id,
        site=SiteResult(
            thermal_comfort_gridcode=context.thermal_comfort_gridcode,
            thermal_comfort_label=context.thermal_comfort_label,
            svf_mean=context.svf_mean,
            canyon_hw_ratio=context.canyon_hw_ratio,
            dominant_wind_direction=context.dominant_wind_direction,
            summer_mean_wind_m_s=context.summer_mean_wind_m_s,
            july_diurnal_swing_C=context.july_diurnal_swing_C,
            summer_CDH_above_26C=context.summer_CDH_above_26C,
        ),
        diagnosis=DiagnosisResult(
            risk_level=diagnosis.overheating_risk_level,
            proxy_odh=diagnosis.estimated_proxy_ODH,
            critical_facades=diagnosis.critical_facades,
            ventilation_deficit=diagnosis.ventilation_deficit,
            night_purge_viable=diagnosis.night_purge_viable,
            diagnosis_text=diagnosis.diagnosis_text,
        ),
        strategies=[
            StrategyResult(
                rank=s["rank"],
                name=s["name"],
                precondition_met=s["precondition_met"],
                precondition_reason=s["precondition_reason"],
                impact_score=s["impact_score"],
                impact_level=s["impact_level"],
                affected_elements=s["affected_elements"],
                key_driver=s["key_driver"],
                factor_scores=s["factor_scores"],
                recommendation=s["recommendation"],
            )
            for s in report.strategies
        ],
    )
