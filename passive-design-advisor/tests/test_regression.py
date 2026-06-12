"""
Regression tests for the bugs found in the 2026-06 debugging pass:
1. Facade extraction silently dropped almost all walls (closed-solid normal
   averaging cancels to ~0) — the real Duplex model must yield many facades.
2. compute_shgi multiplied by (1 - shading_factor), zeroing the gain of
   unshaded facades — shading semantics must be transmission (1.0 = full gain).
"""

from pathlib import Path

import pytest

from src.ifc_parser import FacadeFeature, parse_ifc
from src.thermal_diagnosis import compute_shgi
from src.utils import resolve_path

DUPLEX = resolve_path("data/ifc/Duplex_A_20110907.ifc")


def make_facade(shading_factor: float, orientation: str = "S") -> FacadeFeature:
    return FacadeFeature(
        element_id="test-wall",
        orientation_deg=180.0,
        orientation_label=orientation,
        gross_area_m2=30.0,
        window_area_m2=9.0,
        wwr=0.3,
        window_element_ids=["w1"],
        u_value=None,
        construction_mass="medium",
        shading_factor=shading_factor,
        is_exterior=True,
    )


# ── SHGI shading semantics ────────────────────────────────────────────────────

def test_unshaded_facade_gains_more_than_shaded():
    lat, lon = 41.3851, 2.1734
    unshaded = compute_shgi(make_facade(1.0), lat, lon)
    shaded   = compute_shgi(make_facade(0.3), lat, lon)
    assert unshaded > 0, "unshaded south facade must have non-zero solar gain"
    assert unshaded > shaded
    # gain scales linearly with transmission
    assert shaded == pytest.approx(unshaded * 0.3, rel=1e-6)


# ── Real-model facade extraction ──────────────────────────────────────────────

@pytest.mark.skipif(not DUPLEX.exists(), reason="Duplex sample IFC not present")
class TestDuplexParsing:
    @pytest.fixture(scope="class")
    def building(self):
        return parse_ifc(str(DUPLEX), 41.3851, 2.1734, "residential")

    def test_extracts_many_facades(self, building):
        # The Duplex model has ~45 exterior walls; the old code kept 1.
        assert len(building.facades) >= 20

    def test_facades_have_windows(self, building):
        total_window_area = sum(f.window_area_m2 for f in building.facades)
        assert total_window_area > 5.0

    def test_multiple_orientations(self, building):
        labels = {f.orientation_label for f in building.facades}
        assert len(labels) >= 3, f"expected several orientations, got {labels}"

    def test_facade_areas_plausible(self, building):
        for f in building.facades:
            assert 0.1 <= f.gross_area_m2 <= 500.0
            assert 0.0 <= f.wwr <= 1.0

    def test_roof_extracted(self, building):
        assert building.roof.area_m2 > 1.0
