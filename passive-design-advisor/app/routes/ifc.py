"""
/api/ifc — IFC upload, parsing, and file-serving endpoints.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.models import FacadeOut, ParsedBuilding, RoofOut
from app.session import session_store
from src.ifc_parser import parse_ifc

router = APIRouter(prefix="/api/ifc", tags=["ifc"])

UPLOADS_DIR = Path("uploads")
UPLOADS_DIR.mkdir(exist_ok=True)


@router.post("/upload", response_model=ParsedBuilding)
async def upload_ifc(
    file: UploadFile = File(...),
    site_lat: float = Form(41.3851),
    site_lon: float = Form(2.1734),
    building_use: str = Form("residential"),
):
    if not file.filename.lower().endswith(".ifc"):
        raise HTTPException(status_code=400, detail="Only .ifc files are accepted.")

    session_id = str(uuid.uuid4())
    dest = UPLOADS_DIR / f"{session_id}.ifc"

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        building = parse_ifc(str(dest), site_lat, site_lon, building_use)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail=f"IFC parsing failed: {e}")

    session_store[session_id] = {
        "ifc_path": str(dest),
        "building": building,
    }

    return ParsedBuilding(
        session_id=session_id,
        ifc_filename=file.filename,
        total_floor_area_m2=building.total_floor_area_m2,
        floor_to_ceiling_height_m=building.floor_to_ceiling_height_m,
        building_depth_m=building.building_depth_m,
        building_width_m=building.building_width_m,
        number_of_floors=building.number_of_floors,
        has_opposing_openings=building.has_opposing_openings,
        operable_window_area_m2=building.operable_window_area_m2,
        facades=[
            FacadeOut(
                element_id=f.element_id,
                orientation_deg=f.orientation_deg,
                orientation_label=f.orientation_label,
                gross_area_m2=f.gross_area_m2,
                window_area_m2=f.window_area_m2,
                wwr=f.wwr,
                construction_mass=f.construction_mass,
                shading_factor=f.shading_factor,
            )
            for f in building.facades
        ],
        roof=RoofOut(
            element_id=building.roof.element_id,
            area_m2=building.roof.area_m2,
            is_exposed=building.roof.is_exposed,
            inclination_deg=building.roof.inclination_deg,
            construction_mass=building.roof.construction_mass,
        ),
    )


@router.get("/file/{session_id}")
async def serve_ifc_file(session_id: str):
    """Serve the raw IFC file for the browser-side viewer to load."""
    session = session_store.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found.")
    path = Path(session["ifc_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="IFC file not on disk.")
    return FileResponse(
        str(path),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f"inline; filename={session_id}.ifc"},
    )
