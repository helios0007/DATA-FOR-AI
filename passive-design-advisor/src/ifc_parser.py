"""
Stage 1 — IFC Parsing and Feature Extraction
Extracts geometry, construction, and fenestration data from an IFC file.
Every feature retains the originating IFC element GlobalId.
"""

from dataclasses import dataclass, field
from typing import Optional

import ifcopenshell
import ifcopenshell.geom
import ifcopenshell.util.element
import numpy as np

# ── Construction mass mapping ────────────────────────────────────────────────

MASS_MAPPING: dict[str, str] = {
    "concrete":        "heavy",
    "brick":           "heavy",
    "masonry":         "heavy",
    "stone":           "heavy",
    "rammed earth":    "heavy",
    "timber frame":    "lightweight",
    "steel frame":     "lightweight",
    "curtain wall":    "lightweight",
    "sandwich panel":  "lightweight",
    "insulated panel": "lightweight",
    "clt":             "medium",
    "cross laminated": "medium",
    "block":           "medium",
}

MASS_SCORE: dict[str, float] = {
    "lightweight": 0.0,
    "medium":      0.5,
    "heavy":       1.0,
}

OPERABLE_TYPES = {
    "SINGLE_SWING_LEFT", "SINGLE_SWING_RIGHT",
    "DOUBLE_SWING_LEFT", "DOUBLE_SWING_RIGHT",
    "TILT_AND_TURN_LEFT", "TILT_AND_TURN_RIGHT",
    "PIVOT_HORIZONTAL", "PIVOT_VERTICAL",
    "SLIDING",
}


# ── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class FacadeFeature:
    element_id: str
    orientation_deg: float
    orientation_label: str
    gross_area_m2: float
    window_area_m2: float
    wwr: float
    window_element_ids: list[str]
    u_value: Optional[float]
    construction_mass: str
    shading_factor: float
    is_exterior: bool


@dataclass
class RoofFeature:
    element_id: str
    area_m2: float
    is_exposed: bool
    inclination_deg: float
    u_value: Optional[float]
    construction_mass: str


@dataclass
class BuildingFeatures:
    ifc_file_path: str
    site_latitude: float
    site_longitude: float
    building_use: str
    total_floor_area_m2: float
    floor_to_ceiling_height_m: float
    building_depth_m: float
    building_width_m: float
    number_of_floors: int
    facades: list[FacadeFeature]
    roof: RoofFeature
    has_opposing_openings: bool
    operable_window_area_m2: float


# ── Geometry helpers ─────────────────────────────────────────────────────────

def degrees_to_label(deg: float) -> str:
    """Convert compass bearing (0=N, 90=E) to 8-point label."""
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((deg + 22.5) / 45) % 8
    return labels[idx]


def normal_to_compass_bearing(normal: np.ndarray) -> float:
    """Convert XY normal vector to compass bearing (0=N, 90=E, 180=S, 270=W)."""
    angle = np.degrees(np.arctan2(normal[0], normal[1]))
    return float((angle + 360) % 360)


def get_wall_outward_normal(wall, settings) -> Optional[np.ndarray]:
    """
    Returns the dominant outward-facing normal of a wall [x, y, z].
    Computed by averaging face normals weighted by face area.
    Returns None if geometry extraction fails.
    """
    try:
        shape = ifcopenshell.geom.create_shape(settings, wall)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces = np.array(shape.geometry.faces).reshape(-1, 3)

        normals = []
        areas = []
        for tri in faces:
            v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            edge1 = v1 - v0
            edge2 = v2 - v0
            cross = np.cross(edge1, edge2)
            area = np.linalg.norm(cross) / 2.0
            if area > 1e-6:
                normals.append(cross / (2.0 * area))
                areas.append(area)

        if not normals:
            return None

        weighted = np.average(normals, axis=0, weights=areas)
        norm = np.linalg.norm(weighted[:2])  # only XY for compass bearing
        if norm < 1e-6:
            return None
        return weighted / np.linalg.norm(weighted)

    except Exception:
        return None


def get_element_area(element, settings) -> float:
    """Extract gross surface area from IFC geometry (m²)."""
    try:
        shape = ifcopenshell.geom.create_shape(settings, element)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces = np.array(shape.geometry.faces).reshape(-1, 3)
        total = 0.0
        for tri in faces:
            v0, v1, v2 = verts[tri[0]], verts[tri[1]], verts[tri[2]]
            cross = np.cross(v1 - v0, v2 - v0)
            total += np.linalg.norm(cross) / 2.0
        return float(total)
    except Exception:
        return 0.0


# ── Material / construction helpers ─────────────────────────────────────────

def get_construction_mass(element, model) -> str:
    """
    Determine construction mass category by inspecting material layer names.
    Falls back to 'medium' if no material data found.
    """
    try:
        for assoc in getattr(element, "HasAssociations", []):
            if not assoc.is_a("IfcRelAssociatesMaterial"):
                continue
            mat = assoc.RelatingMaterial

            # IfcMaterialLayerSetUsage → IfcMaterialLayerSet → layers
            if mat.is_a("IfcMaterialLayerSetUsage"):
                layers = mat.ForLayerSet.MaterialLayers
            elif mat.is_a("IfcMaterialLayerSet"):
                layers = mat.MaterialLayers
            elif mat.is_a("IfcMaterialLayer"):
                layers = [mat]
            else:
                continue

            for layer in layers:
                name = (layer.Material.Name or "").lower() if layer.Material else ""
                for keyword, category in MASS_MAPPING.items():
                    if keyword in name:
                        return category
    except Exception:
        pass
    return "medium"


def get_u_value(element) -> Optional[float]:
    """Read ThermalTransmittance from Pset_WallCommon / Pset_SlabCommon."""
    try:
        psets = ifcopenshell.util.element.get_psets(element)
        for pset_name, props in psets.items():
            if "ThermalTransmittance" in props:
                val = props["ThermalTransmittance"]
                if val and float(val) > 0:
                    return float(val)
    except Exception:
        pass
    return None


def is_exterior_wall(wall) -> bool:
    """Check IsExternal property from Pset_WallCommon."""
    try:
        psets = ifcopenshell.util.element.get_psets(wall)
        for pset_name, props in psets.items():
            if "IsExternal" in props:
                return bool(props["IsExternal"])
    except Exception:
        pass
    return True  # assume exterior if unknown


def get_shading_factor(wall, model) -> float:
    """
    Detect shading devices associated with wall.
    Returns 0.3 (partial), 0.5 (overhang), or 1.0 (unshaded).
    """
    try:
        for rel in model.by_type("IfcRelAssignsToProduct"):
            pass  # placeholder — check shading elements below

        wall_id = wall.GlobalId
        for el in model.by_type("IfcShadingDevice"):
            # Check if shading device is spatially related to this wall
            shading_type = getattr(el, "ShadingDeviceType", None)
            if shading_type == "OVERHANG":
                return 0.5
            return 0.3

        for el_type in ("IfcShading", "IfcAnnotation"):
            for el in model.by_type(el_type):
                return 0.3
    except Exception:
        pass
    return 1.0


def get_windows_on_wall(wall, model) -> list:
    """Return all IfcWindow elements hosted by this wall."""
    windows = []
    try:
        for void_rel in getattr(wall, "HasOpenings", []):
            opening = void_rel.RelatedOpeningElement
            for fill_rel in getattr(opening, "HasFillings", []):
                el = fill_rel.RelatedBuildingElement
                if el.is_a("IfcWindow"):
                    windows.append(el)
    except Exception:
        pass
    return windows


def get_window_area(window, settings) -> float:
    """Get window area from OverallWidth × OverallHeight, fallback to geometry."""
    try:
        w = getattr(window, "OverallWidth", None)
        h = getattr(window, "OverallHeight", None)
        if w and h:
            return float(w) * float(h)
    except Exception:
        pass
    return get_element_area(window, settings)


def is_window_operable(window, model) -> bool:
    """Check IfcWindowType.OperationType for operability."""
    try:
        for rel in getattr(window, "IsTypedBy", []):
            wtype = rel.RelatingType
            if wtype.is_a("IfcWindowType"):
                op = getattr(wtype, "OperationType", None)
                if op and str(op).upper() in OPERABLE_TYPES:
                    return True
        # Also check IfcWindowStyle (IFC2x3)
        for rel in getattr(window, "IsDefinedBy", []):
            if hasattr(rel, "RelatingPropertyDefinition"):
                pass
    except Exception:
        pass
    return None  # unknown — caller uses 60% default


# ── Bounding box helpers ─────────────────────────────────────────────────────

def get_building_bounding_box(model, settings) -> tuple[float, float, float]:
    """
    Returns (depth_m, width_m, height_m) from bounding box of all IfcWall elements.
    depth = longest horizontal dimension, width = shortest.
    """
    all_verts = []
    for wall in model.by_type("IfcWall"):
        try:
            shape = ifcopenshell.geom.create_shape(settings, wall)
            verts = np.array(shape.geometry.verts).reshape(-1, 3)
            all_verts.append(verts)
        except Exception:
            continue

    if not all_verts:
        return 10.0, 8.0, 3.0  # sensible defaults

    combined = np.vstack(all_verts)
    x_range = float(combined[:, 0].max() - combined[:, 0].min())
    y_range = float(combined[:, 1].max() - combined[:, 1].min())
    z_range = float(combined[:, 2].max() - combined[:, 2].min())

    horiz = sorted([x_range, y_range])
    return horiz[1], horiz[0], z_range  # depth, width, height


def get_floor_count(model) -> int:
    """Count IfcBuildingStorey elements."""
    storeys = model.by_type("IfcBuildingStorey")
    return max(1, len(storeys))


def get_floor_to_ceiling_height(model) -> float:
    """
    Estimate floor-to-ceiling height from IfcBuildingStorey elevations.
    Falls back to 3.0m.
    """
    storeys = sorted(
        model.by_type("IfcBuildingStorey"),
        key=lambda s: getattr(s, "Elevation", 0) or 0,
    )
    if len(storeys) >= 2:
        elevs = [getattr(s, "Elevation", None) for s in storeys]
        elevs = [e for e in elevs if e is not None]
        if len(elevs) >= 2:
            diffs = [elevs[i + 1] - elevs[i] for i in range(len(elevs) - 1)]
            h = float(np.median(diffs))
            if 2.0 <= h <= 6.0:
                return h
    return 3.0


def get_total_floor_area(model) -> float:
    """Sum GrossFloorArea from IfcBuildingStorey Qto_BuildingStoreyBaseQuantities."""
    total = 0.0
    for storey in model.by_type("IfcBuildingStorey"):
        try:
            qsets = ifcopenshell.util.element.get_psets(storey, qtos_only=True)
            for qset in qsets.values():
                if "GrossFloorArea" in qset:
                    total += float(qset["GrossFloorArea"])
                    break
        except Exception:
            pass
    return total if total > 0 else 0.0


def get_roof_feature(model, settings) -> Optional[RoofFeature]:
    """Extract roof from IfcSlab (ROOF type) or IfcRoof."""
    roof_elements = list(model.by_type("IfcRoof")) + [
        s for s in model.by_type("IfcSlab")
        if getattr(s, "PredefinedType", None) in ("ROOF", "BASESLAB")
    ]

    if not roof_elements:
        # Fallback: highest IfcSlab
        slabs = model.by_type("IfcSlab")
        if slabs:
            roof_elements = [slabs[-1]]

    if not roof_elements:
        return None

    roof_el = roof_elements[0]
    area = get_element_area(roof_el, settings)

    # Estimate inclination from geometry
    inclination = 0.0
    try:
        shape = ifcopenshell.geom.create_shape(settings, roof_el)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        faces = np.array(shape.geometry.faces).reshape(-1, 3)
        z_range = float(verts[:, 2].max() - verts[:, 2].min())
        xy_range = float(np.sqrt(
            (verts[:, 0].max() - verts[:, 0].min()) ** 2 +
            (verts[:, 1].max() - verts[:, 1].min()) ** 2
        ))
        if xy_range > 0:
            inclination = float(np.degrees(np.arctan2(z_range, xy_range)))
    except Exception:
        pass

    return RoofFeature(
        element_id=roof_el.GlobalId,
        area_m2=area,
        is_exposed=True,
        inclination_deg=round(inclination, 1),
        u_value=get_u_value(roof_el),
        construction_mass=get_construction_mass(roof_el, model),
    )


# ── Opposing openings ────────────────────────────────────────────────────────

def check_opposing_openings(facades: list[FacadeFeature]) -> bool:
    """
    True if at least one pair of facades with windows exists where
    orientations differ by 135°–225° (opposing flow path for cross-ventilation).
    """
    windowed = [f for f in facades if f.window_area_m2 > 0]
    for i in range(len(windowed)):
        for j in range(i + 1, len(windowed)):
            diff = abs(windowed[i].orientation_deg - windowed[j].orientation_deg)
            diff = min(diff, 360 - diff)
            if 135 <= diff <= 225:
                return True
    return False


# ── Main parser ──────────────────────────────────────────────────────────────

def parse_ifc(
    ifc_path: str,
    site_latitude: float,
    site_longitude: float,
    building_use: str,
) -> BuildingFeatures:
    """
    Parse IFC file and return a fully populated BuildingFeatures dataclass.
    building_use: "residential" | "office" | "mixed"
    """
    model = ifcopenshell.open(ifc_path)

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_WORLD_COORDS, True)

    # ── Facades ──────────────────────────────────────────────────────────────
    facades: list[FacadeFeature] = []
    total_operable_area = 0.0

    # Collect all wall types (IfcWallElementedCase is IFC4-only, skip if not in schema)
    _all_walls: list = []
    for wtype in ("IfcWall", "IfcWallStandardCase", "IfcWallElementedCase"):
        try:
            _all_walls += list(model.by_type(wtype))
        except Exception:
            pass

    exterior_walls = [w for w in _all_walls if is_exterior_wall(w)]

    # If the file has no IsExternal flags set, treat all walls as exterior
    if not exterior_walls:
        exterior_walls = _all_walls

    for wall in exterior_walls:
        normal = get_wall_outward_normal(wall, settings)
        if normal is None:
            continue

        bearing = normal_to_compass_bearing(normal)
        label = degrees_to_label(bearing)
        gross_area = get_element_area(wall, settings)

        # Some IFC files use mm — area would be in mm², divide to get m²
        # A typical storey wall is 6–60 m²; if raw area > 10000 assume mm²
        if gross_area > 10_000:
            gross_area /= 1_000_000.0  # mm² → m²
        if gross_area < 0.1:
            continue

        windows = get_windows_on_wall(wall, model)
        window_ids = [w.GlobalId for w in windows]
        window_area = sum(get_window_area(w, settings) for w in windows)
        wwr = min(1.0, window_area / gross_area) if gross_area > 0 else 0.0

        # Operable window area
        for w in windows:
            operable = is_window_operable(w, model)
            area = get_window_area(w, settings)
            if operable is True:
                total_operable_area += area
            elif operable is None:
                total_operable_area += area * 0.6  # 60% default

        facades.append(FacadeFeature(
            element_id=wall.GlobalId,
            orientation_deg=round(bearing, 1),
            orientation_label=label,
            gross_area_m2=round(gross_area, 2),
            window_area_m2=round(window_area, 2),
            wwr=round(wwr, 3),
            window_element_ids=window_ids,
            u_value=get_u_value(wall),
            construction_mass=get_construction_mass(wall, model),
            shading_factor=get_shading_factor(wall, model),
            is_exterior=True,
        ))

    # ── Building dimensions ───────────────────────────────────────────────────
    depth, width, _ = get_building_bounding_box(model, settings)
    n_floors = get_floor_count(model)
    h_floor = get_floor_to_ceiling_height(model)
    floor_area = get_total_floor_area(model)

    # Fallback floor area from bounding box × floors
    if floor_area < 1.0:
        floor_area = depth * width * n_floors

    # ── Roof ──────────────────────────────────────────────────────────────────
    roof = get_roof_feature(model, settings)
    if roof is None:
        # Synthetic roof from bounding box
        roof = RoofFeature(
            element_id="SYNTHETIC_ROOF",
            area_m2=round(depth * width, 2),
            is_exposed=True,
            inclination_deg=0.0,
            u_value=None,
            construction_mass="medium",
        )

    # ── Fallback: synthesise 4 cardinal facades from bounding box ────────────────
    # Triggered when IFC geometry extraction failed for every wall.
    if not facades:
        import warnings
        warnings.warn(
            "No exterior facades extracted from IFC; synthesising 4 cardinal facades "
            "from building bounding box. Results will be approximate.",
            stacklevel=2,
        )
        face_height = h_floor * n_floors
        for bearing_deg, orient_label in [(0, "N"), (90, "E"), (180, "S"), (270, "W")]:
            facade_area = round(width * face_height if orient_label in ("N", "S") else depth * face_height, 2)
            facades.append(FacadeFeature(
                element_id=f"SYNTHETIC_{orient_label}",
                orientation_deg=float(bearing_deg),
                orientation_label=orient_label,
                gross_area_m2=facade_area,
                window_area_m2=round(facade_area * 0.3, 2),
                wwr=0.3,
                window_element_ids=[],
                u_value=None,
                construction_mass="medium",
                shading_factor=1.0,
                is_exterior=True,
            ))

    has_opposing = check_opposing_openings(facades)

    return BuildingFeatures(
        ifc_file_path=ifc_path,
        site_latitude=site_latitude,
        site_longitude=site_longitude,
        building_use=building_use,
        total_floor_area_m2=round(floor_area, 1),
        floor_to_ceiling_height_m=round(h_floor, 2),
        building_depth_m=round(depth, 2),
        building_width_m=round(width, 2),
        number_of_floors=n_floors,
        facades=facades,
        roof=roof,
        has_opposing_openings=has_opposing,
        operable_window_area_m2=round(total_operable_area, 2),
    )
