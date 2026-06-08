"""Pydantic models for API request/response serialisation."""

from typing import Optional
from pydantic import BaseModel


# ── IFC upload response ───────────────────────────────────────────────────────

class FacadeOut(BaseModel):
    element_id: str
    orientation_deg: float
    orientation_label: str
    gross_area_m2: float
    window_area_m2: float
    wwr: float
    construction_mass: str
    shading_factor: float

class RoofOut(BaseModel):
    element_id: str
    area_m2: float
    is_exposed: bool
    inclination_deg: float
    construction_mass: str

class ParsedBuilding(BaseModel):
    session_id: str              # UUID, used in subsequent calls
    ifc_filename: str
    total_floor_area_m2: float
    floor_to_ceiling_height_m: float
    building_depth_m: float
    building_width_m: float
    number_of_floors: int
    has_opposing_openings: bool
    operable_window_area_m2: float
    facades: list[FacadeOut]
    roof: RoofOut
    # Raw IFC file path on server (not exposed to client)
    _ifc_path: str = ""


# ── Analysis request ──────────────────────────────────────────────────────────

class AnalysisRequest(BaseModel):
    session_id: str
    site_lat: float
    site_lon: float
    building_use: str            # "residential" | "office" | "mixed"
    rotation_offset_deg: float = 0.0   # user-applied orientation rotation
    shgc: float = 0.6
    skip_llm: bool = False


# ── Analysis response ─────────────────────────────────────────────────────────

class FactorDetail(BaseModel):
    raw: object
    mu: float
    weighted: float

class StrategyResult(BaseModel):
    rank: int
    name: str
    precondition_met: str
    precondition_reason: str
    impact_score: float
    impact_level: str
    affected_elements: list[str]
    key_driver: str
    factor_scores: dict
    recommendation: str

class DiagnosisResult(BaseModel):
    risk_level: str
    proxy_odh: float
    critical_facades: list[str]
    ventilation_deficit: bool
    night_purge_viable: bool
    diagnosis_text: str

class SiteResult(BaseModel):
    thermal_comfort_gridcode: int
    thermal_comfort_label: str
    svf_mean: float
    canyon_hw_ratio: float
    dominant_wind_direction: str
    summer_mean_wind_m_s: float
    july_diurnal_swing_C: float
    summer_CDH_above_26C: float

class AnalysisResponse(BaseModel):
    session_id: str
    site: SiteResult
    diagnosis: DiagnosisResult
    strategies: list[StrategyResult]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str    # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    session_id: str
    messages: list[ChatMessage]
    report_context: Optional[str] = None  # serialised FinalReport summary
