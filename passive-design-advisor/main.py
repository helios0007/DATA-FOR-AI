"""
main.py — CLI entry point for the Passive Design Advisor.

Usage:
    python main.py \\
        --ifc path/to/building.ifc \\
        --lat 41.3851 \\
        --lon 2.1734 \\
        --use residential \\
        --output outputs/reports/

Optional:
    --shgc 0.6          Solar heat gain coefficient (default 0.6)
    --json-only         Suppress markdown output
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich import box

load_dotenv()

from src.ifc_parser import parse_ifc
from src.context_enricher import enrich
from src.thermal_diagnosis import diagnose
from src.strategy_scorer import score_all_strategies
from src.recommender import generate_report

console = Console()

RISK_COLOUR = {
    "LOW":      "green",
    "MEDIUM":   "yellow",
    "HIGH":     "red",
    "CRITICAL": "bold red",
}
LEVEL_COLOUR = {
    "HIGH":   "green",
    "MEDIUM": "yellow",
    "LOW":    "red",
}
PRECONDITION_COLOUR = {
    "YES":     "green",
    "PARTIAL": "yellow",
    "NO":      "red",
}


# ── Console output ────────────────────────────────────────────────────────────

def print_header(building_path: str, lat: float, lon: float):
    console.rule("[bold cyan]PASSIVE DESIGN ADVISOR — Barcelona 2025[/]")
    console.print(f"  IFC: [cyan]{building_path}[/]")
    console.print(f"  SITE: {lat}°N, {lon}°E")


def print_diagnosis(risk_level: str, proxy_odh: float, gridcode: int, comfort_label: str):
    colour = RISK_COLOUR.get(risk_level, "white")
    console.print(f"\n  THERMAL COMFORT ZONE: [yellow]{gridcode} — {comfort_label}[/]")
    console.print(f"  OVERHEATING RISK: [{colour}]{risk_level}[/] (proxy ODH = {proxy_odh:.2f})")


def print_strategy_table(scores):
    console.rule("STRATEGY RECOMMENDATIONS (ranked by impact)")
    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold")
    table.add_column("#",              width=3)
    table.add_column("Strategy",       width=24)
    table.add_column("Level",          width=8)
    table.add_column("Score",          width=9)
    table.add_column("Feasibility",    width=12)

    for i, score in enumerate(scores, start=1):
        lc = LEVEL_COLOUR.get(score.impact_level, "white")
        pc = PRECONDITION_COLOUR.get(score.precondition_met, "white")
        name = score.strategy_name.upper().replace("_", " ")
        table.add_row(
            str(i),
            name,
            f"[{lc}]{score.impact_level}[/]",
            f"{score.impact_score:.0f}/100",
            f"[{pc}]{score.precondition_met}[/]",
        )
    console.print(table)


# ── JSON report ───────────────────────────────────────────────────────────────

def write_json_report(report, output_dir: Path, stem: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{stem}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "metadata":          report.metadata,
                "building_summary":  report.building_summary,
                "site_summary":      report.site_summary,
                "diagnosis":         report.diagnosis_summary,
                "strategies":        report.strategies,
            },
            f, indent=2, ensure_ascii=False,
        )
    return path


# ── Markdown report ───────────────────────────────────────────────────────────

def write_markdown_report(report, output_dir: Path, stem: str) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"{stem}_{ts}.md"
    m = report.metadata
    b = report.building_summary
    s = report.site_summary
    d = report.diagnosis_summary

    lines = [
        "# Passive Design Advisor Report",
        f"**Building:** {m['ifc_file']}",
        f"**Site:** {m['site_lat']}°N, {m['site_lon']}°E",
        f"**Generated:** {m['generated_at']}",
        "**Tool version:** 1.0.0",
        "",
        "---",
        "",
        "## Site Analysis",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Thermal comfort zone | {m['thermal_comfort_zone']} — {s['thermal_comfort_label']} |",
        f"| Sky view factor | {s['svf_mean']:.2f} |",
        f"| Canyon H/W ratio | {s['canyon_hw_ratio']:.1f} |",
        f"| Dominant wind direction | {s['dominant_wind_direction']} |",
        f"| Summer mean wind (EPW) | {s['summer_mean_wind_m_s']:.1f} m/s |",
        f"| July diurnal swing | {s['july_diurnal_swing_C']:.1f}°C |",
        f"| Summer CDH >26°C | {s['summer_CDH_above_26C']:.0f} |",
        "",
        "---",
        "",
        "## Building Summary",
        "",
        "| Parameter | Value |",
        "|---|---|",
        f"| Total floor area | {b['total_floor_area_m2']:.0f} m² |",
        f"| Floors | {b['number_of_floors']} |",
        f"| Floor-to-ceiling height | {b['floor_to_ceiling_height_m']:.1f} m |",
        f"| Building depth | {b['building_depth_m']:.1f} m |",
        f"| Dominant construction | {b['dominant_construction_mass']} |",
        f"| Opposing openings | {b['has_opposing_openings']} |",
        "",
        "---",
        "",
        "## Overheating Diagnosis",
        "",
        f"**Risk level:** {d['risk_level']}",
        f"**Proxy ODH:** {d['proxy_odh']:.2f}",
        "",
        d["diagnosis_text"],
        "",
        f"**Critical elements:** {', '.join(d['critical_facades'])}",
        "",
        "---",
        "",
        "## Strategy Recommendations",
        "",
    ]

    viable   = [s for s in report.strategies if s["precondition_met"] != "NO"]
    excluded = [s for s in report.strategies if s["precondition_met"] == "NO"]

    for entry in viable:
        name  = entry["name"].replace("_", " ").title()
        level = entry["impact_level"]
        score = entry["impact_score"]
        lines += [
            f"### {entry['rank']}. {name} — {level} Impact (Score: {score:.0f}/100)",
            "",
            f"**Precondition:** {entry['precondition_met']} — {entry['precondition_reason']}",
            "",
            f"**Affected elements:** {', '.join(entry['affected_elements'][:6])}",
            "",
            entry["recommendation"],
            "",
            "---",
            "",
        ]

    if excluded:
        lines += ["## Excluded Strategies", ""]
        for entry in excluded:
            name = entry["name"].replace("_", " ").title()
            lines += [
                f"### {name} — NOT FEASIBLE",
                f"**Reason:** {entry['precondition_reason']}",
                "",
            ]

    lines += [
        "---",
        "",
        "## References",
        "",
        "All thresholds and weights in this analysis are derived from the following certified sources:",
        "",
        "- EN 16798-1:2019 Energy performance of buildings — Part 1",
        "- ASHRAE 55:2023 Thermal Environmental Conditions for Human Occupancy",
        "- CIBSE AM10:2005 Natural Ventilation in Non-Domestic Buildings",
        "- CIBSE TM52:2013 The Limits of Thermal Comfort",
        "- Santamouris M. & Asimakopoulos D. 1996 — Passive Cooling of Buildings",
        "- Givoni B. 1994 — Passive and Low Energy Cooling of Buildings",
        "- Balaras C.A. 1996 — The role of thermal mass on the cooling load of buildings",
        "- Lapisa R. et al. 2018 — Optimisation of overheating mitigation strategies",
        "- Evola G. et al. 2017 — Natural ventilation in Mediterranean apartments",
        "- Szokolay S.V. 2004 — Introduction to Architectural Science",
        "- Blocken B. et al. 2007 — CFD simulations of wind flow over urban areas",
        "- Santamouris M. 2014 — Cooling the cities: green roof review",
        "- Getter K.L. & Rowe D.B. 2006 — The role of extensive green roofs",
    ]

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Passive Design Advisor — Barcelona 2025")
    parser.add_argument("--ifc",      required=True,       help="Path to .ifc file")
    parser.add_argument("--lat",      required=True, type=float, help="Site latitude (decimal degrees)")
    parser.add_argument("--lon",      required=True, type=float, help="Site longitude (decimal degrees)")
    parser.add_argument("--use",      required=True, choices=["residential", "office", "mixed"],
                        help="Building use type")
    parser.add_argument("--shgc",     default=0.6,   type=float,
                        help="Solar heat gain coefficient of glazing (default 0.6)")
    parser.add_argument("--output",   default="outputs/reports/",
                        help="Output directory for reports")
    parser.add_argument("--json-only", action="store_true",
                        help="Write JSON report only (skip markdown)")
    parser.add_argument("--skip-llm", action="store_true",
                        help="Skip Stage 5 LLM recommendations (useful when API key is not yet active)")
    args = parser.parse_args()

    ifc_path   = args.ifc
    site_lat   = args.lat
    site_lon   = args.lon
    building_use = args.use
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    ifc_stem   = Path(ifc_path).stem

    print_header(ifc_path, site_lat, site_lon)

    # ── Stage 1 ───────────────────────────────────────────────────────────────
    console.print("\n[dim]Stage 1: Parsing IFC ...[/]")
    building = parse_ifc(ifc_path, site_lat, site_lon, building_use)
    console.print(
        f"  [green]✓[/] {len(building.facades)} exterior facades, "
        f"{building.total_floor_area_m2:.0f} m² floor area, "
        f"{building.number_of_floors} floors"
    )

    # ── Stage 2 ───────────────────────────────────────────────────────────────
    console.print("[dim]Stage 2: Context enrichment ...[/]")
    context = enrich(site_lat, site_lon, building_height_m=building.number_of_floors * building.floor_to_ceiling_height_m)
    console.print(
        f"  [green]✓[/] SVF = {context.svf_mean:.2f}, "
        f"H/W = {context.canyon_hw_ratio:.1f}, "
        f"comfort zone = {context.thermal_comfort_gridcode} ({context.thermal_comfort_label})"
    )

    # ── Stage 3 ───────────────────────────────────────────────────────────────
    console.print("[dim]Stage 3: Thermal diagnosis ...[/]")
    diagnosis = diagnose(building, context, shgc=args.shgc)
    risk_colour = RISK_COLOUR.get(diagnosis.overheating_risk_level, "white")
    console.print(
        f"  [green]✓[/] Risk: [{risk_colour}]{diagnosis.overheating_risk_level}[/] "
        f"(proxy ODH = {diagnosis.estimated_proxy_ODH:.2f})"
    )

    # ── Stage 4 ───────────────────────────────────────────────────────────────
    console.print("[dim]Stage 4: MAUT strategy scoring ...[/]")
    ranked_scores = score_all_strategies(building, context)
    console.print(f"  [green]✓[/] {len(ranked_scores)} strategies scored and ranked")

    # ── Console summary ───────────────────────────────────────────────────────
    print_diagnosis(
        diagnosis.overheating_risk_level,
        diagnosis.estimated_proxy_ODH,
        context.thermal_comfort_gridcode,
        context.thermal_comfort_label,
    )
    print_strategy_table(ranked_scores)

    # ── Stage 5 ───────────────────────────────────────────────────────────────
    console.print("[dim]Stage 5: Generating LLM recommendations ...[/]")
    report = generate_report(building, context, diagnosis, ranked_scores, skip_llm=args.skip_llm)
    console.print("  [green]✓[/] Recommendations generated")

    # ── Write outputs ─────────────────────────────────────────────────────────
    json_path = write_json_report(report, output_dir, ifc_stem)
    console.print(f"\n  JSON report: [cyan]{json_path}[/]")

    if not args.json_only:
        md_path = write_markdown_report(report, output_dir, ifc_stem)
        console.print(f"  Markdown report: [cyan]{md_path}[/]")

    console.rule("[bold green]Done[/]")


if __name__ == "__main__":
    main()
