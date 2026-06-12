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
import ifcopenshell.util.unit
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

# Triangles whose unit normal has |nz| below this are treated as vertical
# (wall face) candidates.
VERTICAL_NZ_LIMIT = 0.6


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


def get_element_triangles(element, settings) -> Optional[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """
    Triangulate an element. Returns (unit_normals, areas, centroids) arrays,
    one row per triangle, or None if geometry extraction fails.
    """
    try:
        shape = ifcopenshell.geom.create_shape(settings, element)
        verts = np.array(shape.geometry.verts).reshape(-1, 3)
        tris  = np.array(shape.geometry.faces).reshape(-1, 3)
        if len(tris) == 0:
            return None

        v0 = verts[tris[:, 0]]
        v1 = verts[tris[:, 1]]
        v2 = verts[tris[:, 2]]
        cross = np.cross(v1 - v0, v2 - v0)
        areas = np.linalg.norm(cross, axis=1) / 2.0
        keep  = areas > 1e-8
        if not keep.any():
            return None

        normals   = cross[keep] / (2.0 * areas[keep])[:, None]
        centroids = (v0[keep] + v1[keep] + v2[keep]) / 3.0
        return normals, areas[keep], centroids
    except Exception:
        return None


def get_dominant_face(
    normals: np.ndarray,
    areas: np.ndarray,
    centroids: np.ndarray,
) -> Optional[tuple[np.ndarray, float, np.ndarray]]:
    """
    Find the dominant vertical face of a wall solid.

    A closed solid's area-weighted normal sum is ~zero (faces cancel pairwise),
    so instead we bin vertical triangles by compass bearing and take the bin
    cluster with the largest total area — that is one of the wall's two big
    faces. Returns (unit_normal, face_area, face_centroid) or None.
    """
    vertical = np.abs(normals[:, 2]) < VERTICAL_NZ_LIMIT
    if not vertical.any():
        return None

    v_normals   = normals[vertical]
    v_areas     = areas[vertical]
    v_centroids = centroids[vertical]

    bearings = (np.degrees(np.arctan2(v_normals[:, 0], v_normals[:, 1])) + 360) % 360
    n_bins   = 16
    bin_idx  = (bearings / (360 / n_bins)).astype(int) % n_bins

    # Accumulate area per bin including immediate neighbours so a face that
    # straddles a bin boundary is not split.
    bin_area = np.zeros(n_bins)
    for b in range(n_bins):
        bin_area[b] = v_areas[bin_idx == b].sum()
    smoothed = bin_area + np.roll(bin_area, 1) + np.roll(bin_area, -1)

    best = int(np.argmax(smoothed))
    members = np.isin(bin_idx, [(best - 1) % n_bins, best, (best + 1) % n_bins])
    if not members.any():
        return None

    face_area     = float(v_areas[members].sum())
    mean_normal   = np.average(v_normals[members], axis=0, weights=v_areas[members])
    norm          = np.linalg.norm(mean_normal)
    if norm < 1e-9 or face_area < 1e-6:
        return None
    face_centroid = np.average(v_centroids[members], axis=0, weights=v_areas[members])
    return mean_normal / norm, face_area, face_centroid


def get_element_area(element, settings) -> float:
    """Extract gross surface area from IFC geometry (m², all faces)."""
    tri = get_element_triangles(element, settings)
    if tri is None:
        return 0.0
    _, areas, _ = tri
    return float(areas.sum())


def get_projected_area(element, settings) -> float:
    """
    Horizontal projected (footprint) area of an element in m².
    Sums |n_z|·area over all triangles, which counts top and bottom faces of a
    slab once each, then halves to get the one-sided footprint.
    """
    tri = get_element_triangles(element, settings)
    if tri is None:
        return 0.0
    normals, areas, _ = tri
    return float(np.sum(np.abs(normals[:, 2]) * areas) / 2.0)


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


def get_shading_factor(wall, model, settings, wall_centroid: Optional[np.ndarray]) -> float:
    """
    Solar transmission factor for the facade:
      1.0 = unshaded, 0.5 = overhang nearby, 0.3 = other shading device nearby.

    A shading device only counts if its centroid lies within 5 m of the wall —
    a device elsewhere in the model must not shade this facade.
    IfcShadingDevice does not exist in the IFC2x3 schema; those files are
    treated as unshaded.
    """
    try:
        devices = model.by_type("IfcShadingDevice")
    except RuntimeError:
        return 1.0  # schema (e.g. IFC2x3) has no IfcShadingDevice entity
    if not devices or wall_centroid is None:
        return 1.0

    for device in devices:
        tri = get_element_triangles(device, settings)
        if tri is None:
            continue
        _, areas, centroids = tri
        device_centroid = np.average(centroids, axis=0, weights=areas)
        if np.linalg.norm(device_centroid - wall_centroid) > 5.0:
            continue
        if str(getattr(device, "PredefinedType", "")) == "OVERHANG":
            return 0.5
        return 0.3
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


def get_window_area(window, settings, unit_scale: float = 1.0) -> float:
    """
    Window area from OverallWidth × OverallHeight (attribute values are in
    project length units, so apply unit_scale to convert to metres).
    Falls back to half the total surface area of the window solid.
    """
    try:
        w = getattr(window, "OverallWidth", None)
        h = getattr(window, "OverallHeight", None)
        if w and h:
            return float(w) * unit_scale * float(h) * unit_scale
    except Exception:
        pass
    return get_element_area(window, settings) / 2.0


def is_window_operable(window, model) -> Optional[bool]:
    """Check IfcWindowType.OperationType for operability. None = unknown."""
    try:
        for rel in getattr(window, "IsTypedBy", []):
            wtype = rel.RelatingType
            if wtype.is_a("IfcWindowType"):
                op = getattr(wtype, "OperationType", None)
                if op and str(op).upper() in OPERABLE_TYPES:
                    return True
    except Exception:
        pass
    return None  # unknown — caller uses 60% default


# ── Storey helpers ───────────────────────────────────────────────────────────

def get_floor_count(model) -> int:
    """Count IfcBuildingStorey elements."""
    storeys = model.by_type("IfcBuildingStorey")
    return max(1, len(storeys))


def get_floor_to_ceiling_height(model, unit_scale: float = 1.0) -> float:
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
        elevs = [e * unit_scale for e in elevs if e is not None]
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
    """
    Extract the roof. Preference order:
      1. IfcRoof (resolving aggregated child slabs for geometry)
      2. IfcSlab with PredefinedType ROOF
      3. The IfcSlab with the highest centroid (top slab)
    BASESLAB (foundation) is never a roof.
    """
    roof_el = None
    geometry_elements: list = []

    roofs = list(model.by_type("IfcRoof"))
    if roofs:
        roof_el = roofs[0]
        # An IfcRoof is often an empty aggregate — geometry lives in child slabs
        children = []
        for rel in getattr(roof_el, "IsDecomposedBy", []) or []:
            children.extend(rel.RelatedObjects)
        geometry_elements = children if children else [roof_el]
    else:
        slabs = [
            s for s in model.by_type("IfcSlab")
            if str(getattr(s, "PredefinedType", "")) == "ROOF"
        ]
        if slabs:
            roof_el = slabs[0]
            geometry_elements = [roof_el]
        else:
            # Highest slab by centroid Z (excluding foundations)
            candidates = []
            for s in model.by_type("IfcSlab"):
                if str(getattr(s, "PredefinedType", "")) == "BASESLAB":
                    continue
                tri = get_element_triangles(s, settings)
                if tri is None:
                    continue
                _, areas, centroids = tri
                z = float(np.average(centroids[:, 2], weights=areas))
                candidates.append((z, s))
            if candidates:
                candidates.sort(key=lambda t: t[0])
                roof_el = candidates[-1][1]
                geometry_elements = [roof_el]

    if roof_el is None:
        return None

    # Projected footprint area + inclination from combined geometry
    area = 0.0
    z_range, xy_range = 0.0, 0.0
    all_verts = []
    for el in geometry_elements:
        area += get_projected_area(el, settings)
        tri = get_element_triangles(el, settings)
        if tri is not None:
            all_verts.append(tri[2])
    if all_verts:
        combined = np.vstack(all_verts)
        z_range  = float(combined[:, 2].max() - combined[:, 2].min())
        xy_range = float(np.sqrt(
            (combined[:, 0].max() - combined[:, 0].min()) ** 2 +
            (combined[:, 1].max() - combined[:, 1].min()) ** 2
        ))

    inclination = float(np.degrees(np.arctan2(z_range, xy_range))) if xy_range > 0 else 0.0

    return RoofFeature(
        element_id=roof_el.GlobalId,
        area_m2=round(area, 2),
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

    try:
        unit_scale = float(ifcopenshell.util.unit.calculate_unit_scale(model))
    except Exception:
        unit_scale = 1.0

    # Collect all wall types (IfcWallElementedCase is IFC4-only, skip if not in schema)
    _all_walls: list = []
    for wtype in ("IfcWall", "IfcWallStandardCase", "IfcWallElementedCase"):
        try:
            _all_walls += list(model.by_type(wtype))
        except Exception:
            pass
    # by_type("IfcWall") already includes subtypes in some schema versions — dedupe
    _all_walls = list({w.id(): w for w in _all_walls}.values())

    exterior_walls = [w for w in _all_walls if is_exterior_wall(w)]

    # If the file has no IsExternal flags set, treat all walls as exterior
    if not exterior_walls:
        exterior_walls = _all_walls

    # ── First pass: triangulate every exterior wall once ─────────────────────
    wall_geometry: dict[int, tuple] = {}   # wall.id() → (normals, areas, centroids)
    all_centroids = []
    all_weights = []
    for wall in exterior_walls:
        tri = get_element_triangles(wall, settings)
        if tri is None:
            continue
        wall_geometry[wall.id()] = tri
        _, areas, centroids = tri
        all_centroids.append(centroids)
        all_weights.append(areas)

    if all_centroids:
        stacked = np.vstack(all_centroids)
        weights = np.concatenate(all_weights)
        building_centroid = np.average(stacked, axis=0, weights=weights)
        x_range = float(stacked[:, 0].max() - stacked[:, 0].min())
        y_range = float(stacked[:, 1].max() - stacked[:, 1].min())
        horiz = sorted([x_range, y_range])
        depth, width = max(horiz[1], 1.0), max(horiz[0], 1.0)
    else:
        building_centroid = np.zeros(3)
        depth, width = 10.0, 8.0   # sensible defaults

    # ── Second pass: build facade features ───────────────────────────────────
    facades: list[FacadeFeature] = []
    total_operable_area = 0.0

    for wall in exterior_walls:
        tri = wall_geometry.get(wall.id())
        if tri is None:
            continue
        face = get_dominant_face(*tri)
        if face is None:
            continue
        normal, face_area, face_centroid = face

        # Orient outward: the outward face normal points away from the
        # building centroid in plan.
        offset_xy = face_centroid[:2] - building_centroid[:2]
        if np.linalg.norm(offset_xy) > 1e-6 and float(np.dot(normal[:2], offset_xy)) < 0:
            normal = -normal

        if np.linalg.norm(normal[:2]) < 1e-6:
            continue   # horizontal face won — not a usable facade

        bearing    = normal_to_compass_bearing(normal)
        label      = degrees_to_label(bearing)
        gross_area = face_area
        if gross_area < 0.1:
            continue

        windows     = get_windows_on_wall(wall, model)
        window_ids  = [w.GlobalId for w in windows]
        window_area = sum(get_window_area(w, settings, unit_scale) for w in windows)
        wwr         = min(1.0, window_area / gross_area) if gross_area > 0 else 0.0

        # Operable window area
        for w in windows:
            operable = is_window_operable(w, model)
            area = get_window_area(w, settings, unit_scale)
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
            shading_factor=get_shading_factor(wall, model, settings, face_centroid),
            is_exterior=True,
        ))

    # ── Building dimensions ───────────────────────────────────────────────────
    n_floors   = get_floor_count(model)
    h_floor    = get_floor_to_ceiling_height(model, unit_scale)
    floor_area = get_total_floor_area(model)

    # Fallback floor area from bounding box × floors
    if floor_area < 1.0:
        floor_area = depth * width * n_floors

    # ── Roof ──────────────────────────────────────────────────────────────────
    roof = get_roof_feature(model, settings)
    if roof is None or roof.area_m2 < 1.0:
        # Synthetic roof from bounding box
        roof = RoofFeature(
            element_id=roof.element_id if roof else "SYNTHETIC_ROOF",
            area_m2=round(depth * width, 2),
            is_exposed=True,
            inclination_deg=roof.inclination_deg if roof else 0.0,
            u_value=roof.u_value if roof else None,
            construction_mass=roof.construction_mass if roof else "medium",
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
