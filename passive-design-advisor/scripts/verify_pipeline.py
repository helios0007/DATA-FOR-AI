"""Smoke-run the full pipeline (stages 1–5, LLM skipped) on the Duplex sample."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.context_enricher import enrich
from src.ifc_parser import parse_ifc
from src.recommender import generate_report
from src.strategy_scorer import score_all_strategies
from src.thermal_diagnosis import diagnose
from src.utils import resolve_path

LAT, LON = 41.3851, 2.1734

t0 = time.perf_counter()
building = parse_ifc(str(resolve_path("data/ifc/Duplex_A_20110907.ifc")), LAT, LON, "residential")
t1 = time.perf_counter()
print(f"[1] parse_ifc           {t1-t0:6.1f}s — {len(building.facades)} facades, "
      f"roof {building.roof.area_m2:.1f} m², windows "
      f"{sum(f.window_area_m2 for f in building.facades):.1f} m²")

context = enrich(LAT, LON, building_height_m=building.number_of_floors * building.floor_to_ceiling_height_m)
t2 = time.perf_counter()
print(f"[2] enrich (cold)       {t2-t1:6.1f}s — SVF {context.svf_mean}, H/W {context.canyon_hw_ratio}, "
      f"zone {context.thermal_comfort_gridcode} ({context.thermal_comfort_label})")

enrich(LAT + 0.001, LON + 0.001, building_height_m=10)
t3 = time.perf_counter()
print(f"[2] enrich (warm)       {t3-t2:6.1f}s")

diagnosis = diagnose(building, context)
t4 = time.perf_counter()
print(f"[3] diagnose            {t4-t3:6.1f}s — risk {diagnosis.overheating_risk_level}, "
      f"ODH {diagnosis.estimated_proxy_ODH}, critical {diagnosis.critical_facades}")

scores = score_all_strategies(building, context)
t5 = time.perf_counter()
print(f"[4] score               {t5-t4:6.1f}s")
for s in scores:
    print(f"      {s.strategy_name:>18}: {s.impact_score:5.1f} {s.impact_level:<6} ({s.precondition_met})")

report = generate_report(building, context, diagnosis, scores, skip_llm=True)
t6 = time.perf_counter()
print(f"[5] report (skip_llm)   {t6-t5:6.1f}s — {len(report.strategies)} strategies")
print(f"TOTAL {t6-t0:.1f}s")
