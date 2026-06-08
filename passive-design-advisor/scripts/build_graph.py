"""
build_graph.py — Builds the NetworkX strategy knowledge graph and saves it
to graph/strategy_graph.json.

Run from project root:
    python scripts/build_graph.py
"""

import json
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

OUTPUT_PATH = Path("graph/strategy_graph.json")

# ── Design option catalogue ───────────────────────────────────────────────────

DESIGN_OPTIONS: dict[str, list[dict]] = {
    "shading": [
        {
            "id": "shading_fixed_louvers",
            "label": "Fixed horizontal louvers",
            "description": (
                "Permanent horizontal fins above windows. Best for south facades. "
                "Sized for latitude 41°N to block summer sun above 60° altitude while admitting "
                "winter sun below 30°. Overhang depth = window height × tan(90° - 60° - lat)."
            ),
            "suitable_for": ["S", "SE", "SW"],
            "performance_note": (
                "Reduces solar heat gain by 50–80% on south facades. Source: Szokolay 2004 §3.4."
            ),
        },
        {
            "id": "shading_operable_blinds",
            "label": "External operable blinds or shutters",
            "description": (
                "User-controlled external roller blinds or venetian shutters. More flexible than "
                "fixed louvers — can be opened in winter or for daylight. Best for E and W facades "
                "where sun angle varies."
            ),
            "suitable_for": ["E", "W", "SE", "SW"],
            "performance_note": (
                "Can reduce solar gain by up to 90% when closed. Source: CIBSE Guide A 2015, Table 6.5."
            ),
        },
        {
            "id": "shading_vegetated_trellis",
            "label": "Vegetated trellis / green facade",
            "description": (
                "Climbing plants on a structural frame 200–400mm from facade surface. Provides "
                "shading AND evapotranspiration cooling effect. Deciduous species preferred."
            ),
            "suitable_for": ["S", "SE", "SW", "E", "W"],
            "performance_note": (
                "Reduces surface temperature by 5–15°C. "
                "Source: Pérez et al. 2011, Renewable and Sustainable Energy Reviews 15(1):576–583."
            ),
        },
        {
            "id": "shading_overhangs",
            "label": "Roof overhangs / cantilevered balconies",
            "description": (
                "Horizontal projection from the building facade. At lat 41°N, summer noon altitude ≈ 72°, "
                "so D ≈ H_window × 0.32 for full shading at summer solstice noon."
            ),
            "suitable_for": ["S", "SE", "SW"],
            "performance_note": "Source: Szokolay 2004 §3.4.2.",
        },
    ],
    "cross_ventilation": [
        {
            "id": "cv_through_building",
            "label": "Through-building cross-ventilation",
            "description": (
                "Open windows on windward and leeward facades simultaneously. "
                "Inlet on prevailing wind side (NE/N for Barcelona), outlet on opposite side. "
                "Inlet area should be 60–70% of outlet area. Source: CIBSE AM10:2005 §3.3."
            ),
            "suitable_for": "buildings with D/H < 5",
            "performance_note": "Achieves 5–15 ACH under moderate wind.",
        },
        {
            "id": "cv_courtyard",
            "label": "Internal courtyard for ventilation",
            "description": (
                "Central courtyard creates pressure differential driving cross-ventilation. "
                "Courtyard width : height ratio should be 1:1 to 2:1."
            ),
            "suitable_for": "deep plan buildings D/H > 3",
            "performance_note": "Source: Santamouris 1996 Ch.8.",
        },
        {
            "id": "cv_wing_walls",
            "label": "Wing walls to direct airflow",
            "description": (
                "Vertical fins flanking windows on windward facade to capture oblique wind. "
                "Fin projection = 0.5–1.0 × window width."
            ),
            "suitable_for": "facades where wind is oblique (>30° from normal)",
            "performance_note": "Increases inlet velocity by 30–50%. Source: Givoni 1994 Ch.4.",
        },
    ],
    "thermal_mass": [
        {
            "id": "tm_exposed_concrete",
            "label": "Exposed concrete or masonry internal surfaces",
            "description": (
                "Leave internal face of concrete walls or floor slabs unfinished or with thin plaster. "
                "Insulation must be placed externally. Minimum 150mm concrete for effective thermal lag. "
                "Thermal admittance > 3 W/m²K required."
            ),
            "performance_note": "Shifts peak indoor temperature by 4–6 hours. Source: Balaras 1996 §3.",
        },
        {
            "id": "tm_pcm",
            "label": "Phase change material (PCM) panels",
            "description": (
                "Microencapsulated PCM integrated into plasterboard or ceiling tiles. "
                "Melting point 23–26°C for Barcelona summer. Typical capacity: 14–30 MJ/m³."
            ),
            "performance_note": (
                "Reduces peak temperature by 2–4°C in lightweight buildings. "
                "Source: Cabeza et al. 2011, Energy and Buildings 43(6):1523–1533."
            ),
        },
        {
            "id": "tm_trombe_wall",
            "label": "Trombe wall (thermal storage wall)",
            "description": (
                "South-facing heavy masonry wall (300–400mm) with glazing 50–150mm in front. "
                "In Barcelona MUST be shaded in summer to prevent overheating."
            ),
            "performance_note": "Source: Szokolay 2004 §4.5.",
        },
    ],
    "night_purge": [
        {
            "id": "np_operable_windows",
            "label": "Secure operable windows for night ventilation",
            "description": (
                "Replace fixed glazing with tilt-and-turn or pivot windows. "
                "Install lockable ventilation position (10–15° opening) for security. "
                "Inlet near floor level, outlet near ceiling. Target: >5% of floor area operable."
            ),
            "performance_note": "Source: CIBSE TM52:2013 §4.2.",
        },
        {
            "id": "np_roof_ventilators",
            "label": "Automated roof ventilators / clerestory openings",
            "description": (
                "Motorised roof vents open automatically when outdoor temp drops below 22°C after sunset. "
                "Stack effect assists flow even in calm conditions."
            ),
            "performance_note": "Stack ventilation adds 1–3 ACH at zero wind. Source: Santamouris 1996 §9.4.",
        },
        {
            "id": "np_cool_tower",
            "label": "Wind tower / cool tower",
            "description": (
                "Vertical tower above roof captures wind and directs it downward. "
                "Effective in Barcelona's sea breeze regime when wind speed > 1.5 m/s."
            ),
            "performance_note": "Passive — no energy consumption. Source: Givoni 1994 Ch.9.",
        },
    ],
    "green_roof": [
        {
            "id": "gr_sedum_mat",
            "label": "Extensive sedum mat (50–100mm substrate)",
            "description": (
                "Lightweight (60–120 kg/m²), low maintenance, drought-tolerant sedum. "
                "Minimum substrate depth 50mm. Irrigation not required after establishment."
            ),
            "performance_note": (
                "Reduces roof surface temperature by 20–30°C vs bare membrane. "
                "Source: Getter & Rowe 2006 §4."
            ),
        },
        {
            "id": "gr_herbaceous",
            "label": "Semi-intensive herbaceous green roof (150–250mm)",
            "description": (
                "Medium substrate depth, wider plant palette. Better evapotranspiration than sedum. "
                "Requires occasional irrigation in Barcelona's dry summers. Load: 120–200 kg/m²."
            ),
            "performance_note": "Source: Santamouris 2014 §5.2.",
        },
        {
            "id": "gr_combined_pv",
            "label": "Green roof combined with photovoltaic panels",
            "description": (
                "Bifacial PV panels elevated 300–500mm above green roof substrate. "
                "Green roof reduces ambient temperature (improves PV efficiency 3–5%). "
                "PV panels shade substrate (reduces irrigation need)."
            ),
            "performance_note": (
                "Source: Chemisana & Lamnatou 2014, Applied Energy 119:47–54."
            ),
        },
    ],
}

# ── Literature / standard nodes ───────────────────────────────────────────────

LITERATURE_NODES: list[dict] = [
    {"id": "EN16798_1",        "type": "standard", "label": "EN 16798-1:2019"},
    {"id": "ASHRAE55_2023",    "type": "standard", "label": "ASHRAE 55:2023"},
    {"id": "CIBSE_AM10",       "type": "standard", "label": "CIBSE AM10:2005"},
    {"id": "CIBSE_TM52",       "type": "standard", "label": "CIBSE TM52:2013"},
    {"id": "ISO13786",         "type": "standard", "label": "ISO 13786:2017"},
    {"id": "santamouris_1996", "type": "paper",    "label": "Santamouris 1996"},
    {"id": "givoni_1994",      "type": "paper",    "label": "Givoni 1994"},
    {"id": "balaras_1996",     "type": "paper",    "label": "Balaras 1996"},
    {"id": "lapisa_2018",      "type": "paper",    "label": "Lapisa et al. 2018"},
    {"id": "evola_2017",       "type": "paper",    "label": "Evola et al. 2017"},
    {"id": "szokolay_2004",    "type": "paper",    "label": "Szokolay 2004"},
    {"id": "blocken_2007",     "type": "paper",    "label": "Blocken et al. 2007"},
    {"id": "santamouris_2014", "type": "paper",    "label": "Santamouris 2014"},
    {"id": "getter_rowe_2006", "type": "paper",    "label": "Getter & Rowe 2006"},
]


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    # ── Strategy nodes ────────────────────────────────────────────────────────
    for strategy in ["shading", "cross_ventilation", "thermal_mass", "night_purge", "green_roof"]:
        G.add_node(strategy, type="strategy", label=strategy)

    # ── Design option nodes ───────────────────────────────────────────────────
    for strategy, options in DESIGN_OPTIONS.items():
        for opt in options:
            G.add_node(opt["id"], type="design_option", **opt)
            G.add_edge(strategy, opt["id"], relation="has_variant")

    # ── Literature nodes ──────────────────────────────────────────────────────
    for node in LITERATURE_NODES:
        G.add_node(node["id"], **node)

    # ── Justification edges ───────────────────────────────────────────────────
    justifications = [
        ("shading",           "lapisa_2018",      "factor weights from Table 3"),
        ("shading",           "szokolay_2004",    "orientation weights §2.3"),
        ("shading",           "santamouris_1996", "GHI threshold §4.2"),
        ("cross_ventilation", "CIBSE_AM10",       "D/H limit §3.4"),
        ("cross_ventilation", "santamouris_1996", "wind speed weights Table 8.3"),
        ("cross_ventilation", "givoni_1994",      "opposing outlets Ch.3"),
        ("cross_ventilation", "blocken_2007",     "canyon correction Table 3"),
        ("thermal_mass",      "balaras_1996",     "diurnal swing weights"),
        ("thermal_mass",      "givoni_1994",      "diurnal swing threshold Ch.6"),
        ("thermal_mass",      "ISO13786",         "mass classification"),
        ("night_purge",       "santamouris_1996", "cooling hours threshold §9.3"),
        ("night_purge",       "CIBSE_TM52",       "opening area §4.2"),
        ("green_roof",        "santamouris_2014", "SVF threshold §4.1"),
        ("green_roof",        "getter_rowe_2006", "gridcode weights"),
    ]
    for src, dst, note in justifications:
        G.add_edge(src, dst, relation="justified_by", note=note)

    # ── Synergy edges ─────────────────────────────────────────────────────────
    G.add_edge(
        "thermal_mass", "night_purge",
        relation="synergy_with",
        note="Thermal mass absorbs daytime heat; night purge discharges it. Combined effect > sum of parts. Source: Balaras 1996 §4.",
    )
    G.add_edge(
        "shading", "cross_ventilation",
        relation="synergy_with",
        note="Shading reduces solar gain, lowering indoor temp, increasing ventilation effectiveness. Source: Evola et al. 2017.",
    )

    # ── Compatibility edges ───────────────────────────────────────────────────
    G.add_edge(
        "thermal_mass", "cross_ventilation",
        relation="no_conflict",
        note="Compatible — heavy construction does not impede ventilation.",
    )
    G.add_edge(
        "shading", "thermal_mass",
        relation="no_conflict",
        note="Compatible — shading reduces peak load that mass must handle.",
    )

    return G


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    G = build_graph()

    data = json_graph.node_link_data(G)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Strategy graph written to {OUTPUT_PATH}")
    print(f"  Nodes: {G.number_of_nodes()}")
    print(f"  Edges: {G.number_of_edges()}")


if __name__ == "__main__":
    main()
