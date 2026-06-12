"""
/api/analysis — Run the full pipeline (Stages 2–5) for a session.
Accepts site coordinates, rotation offset, and building use.
Returns scored strategies + thermal diagnosis.

Two entry points:
  POST /api/analysis/run         — classic request/response
  POST /api/analysis/run-stream  — SSE: stage progress events, then the result

Endpoints are plain `def` so FastAPI runs them in its threadpool — the
pipeline is CPU/IO heavy and must not block the event loop.
"""

import json
from copy import deepcopy

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models import (
    AnalysisRequest, AnalysisResponse,
    DiagnosisResult, SiteResult, StrategyResult,
)
from app.session import session_store
from src.context_enricher import enrich
from src.ifc_parser import BuildingFeatures, degrees_to_label
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

    rotated = deepcopy(building)
    for facade in rotated.facades:
        new_deg = (facade.orientation_deg + offset_deg) % 360
        facade.orientation_deg = round(new_deg, 1)
        facade.orientation_label = degrees_to_label(new_deg)
    return rotated


def _prepare_building(req: AnalysisRequest) -> BuildingFeatures:
    session = session_store.get(req.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found. Upload an IFC file first.")

    building: BuildingFeatures = deepcopy(session["building"])
    building.site_latitude  = req.site_lat
    building.site_longitude = req.site_lon
    building.building_use   = req.building_use
    return _apply_rotation(building, req.rotation_offset_deg)


def _build_response(req, context, diagnosis, report) -> AnalysisResponse:
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


def _run_pipeline(req: AnalysisRequest, building: BuildingFeatures):
    """Run stages 2–5, storing results in the session. Yields after each stage."""
    session = session_store[req.session_id]

    yield "enrich", "Analysing site context (SVF, street canyon, comfort zone)…"
    context = enrich(
        req.site_lat, req.site_lon,
        building_height_m=building.number_of_floors * building.floor_to_ceiling_height_m,
    )

    yield "diagnose", "Running thermal diagnosis (solar gains per facade)…"
    diagnosis = diagnose(building, context, shgc=req.shgc)

    yield "score", "Scoring passive strategies (MAUT)…"
    ranked_scores = score_all_strategies(building, context)

    yield "recommend", "Generating recommendations…"
    report = generate_report(building, context, diagnosis, ranked_scores, skip_llm=req.skip_llm)

    session["report"] = report
    session["context"] = context
    session["diagnosis"] = diagnosis
    yield "done", _build_response(req, context, diagnosis, report)


STAGE_ERRORS = {
    "enrich": "Context enrichment failed",
    "diagnose": "Thermal diagnosis failed",
    "score": "Strategy scoring failed",
    "recommend": "Recommendation generation failed",
}


@router.post("/run", response_model=AnalysisResponse)
def run_analysis(req: AnalysisRequest):
    building = _prepare_building(req)

    stage = "enrich"
    try:
        for stage, payload in _run_pipeline(req, building):
            if stage == "done":
                return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{STAGE_ERRORS.get(stage, 'Analysis failed')}: {e}")

    raise HTTPException(status_code=500, detail="Analysis did not complete.")


@router.post("/run-stream")
def run_analysis_stream(req: AnalysisRequest):
    """
    Same pipeline, but streamed as Server-Sent Events so the UI can show
    per-stage progress. Events:
      data: {"stage": "enrich", "label": "..."}      (one per stage start)
      data: {"stage": "done", "result": {...}}        (AnalysisResponse)
      data: {"stage": "error", "detail": "..."}       (on failure)
    """
    building = _prepare_building(req)

    def events():
        stage = "enrich"
        try:
            for stage, payload in _run_pipeline(req, building):
                if stage == "done":
                    yield "data: " + json.dumps(
                        {"stage": "done", "result": payload.model_dump()}
                    ) + "\n\n"
                else:
                    yield "data: " + json.dumps({"stage": stage, "label": payload}) + "\n\n"
        except Exception as e:
            yield "data: " + json.dumps(
                {"stage": "error", "detail": f"{STAGE_ERRORS.get(stage, 'Analysis failed')}: {e}"}
            ) + "\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
