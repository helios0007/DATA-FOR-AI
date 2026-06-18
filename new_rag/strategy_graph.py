from __future__ import annotations


STRATEGIES = {
    "building_envelope": {
        "label": "Building envelope retrofit",
        "keywords": [
            "building envelope",
            "envelope",
            "retrofit",
            "insulation",
            "thermal bridge",
            "airtightness",
        ],
    },
    "external_insulation": {
        "label": "External insulation",
        "keywords": [
            "external insulation",
            "external wall",
            "facade insulation",
            "continuous insulation",
            "thermal mass",
        ],
    },
    "internal_insulation": {
        "label": "Internal insulation",
        "keywords": [
            "internal insulation",
            "inside insulation",
            "thermal capacity",
            "thermal stress",
            "floor area",
        ],
    },
    "roof_attic": {
        "label": "Roof and attic insulation",
        "keywords": [
            "roof",
            "attic",
            "vapour barrier",
            "condensation",
            "pitched roof",
            "flat roof",
        ],
    },
    "windows_shading": {
        "label": "Windows and shading",
        "keywords": [
            "window",
            "glazing",
            "shading",
            "overheating",
            "solar gain",
            "summer",
        ],
    },
    "hvac_services": {
        "label": "HVAC and service modules",
        "keywords": [
            "hvac",
            "dhw",
            "heating",
            "service module",
            "centralised",
            "decentralised",
        ],
    },
    "solar_integration": {
        "label": "Active solar integration",
        "keywords": [
            "solar",
            "photovoltaic",
            "pv",
            "solar thermal",
            "collector",
            "orientation",
        ],
    },
}


DESIGN_OPTIONS = {
    "external_insulation": [
        {
            "id": "continuous_external_insulation",
            "label": "Continuous external insulation",
            "description": "External insulation layer wrapped around the building envelope to reduce thermal bridges.",
        },
        {
            "id": "new_facade_finish",
            "label": "New facade finish",
            "description": "Rendering, lightweight facade systems, or outer brick blade installed over insulation.",
        },
    ],
    "internal_insulation": [
        {
            "id": "inside_stud_wall_insulation",
            "label": "Inside stud-wall insulation",
            "description": "New internal lining with insulation where external solutions are not feasible.",
        }
    ],
    "roof_attic": [
        {
            "id": "warm_side_vapour_barrier",
            "label": "Warm-side vapour barrier",
            "description": "Vapour barrier placed on the warm side of insulation to reduce condensation risk.",
        },
        {
            "id": "cold_attic_floor_insulation",
            "label": "Cold attic floor insulation",
            "description": "Insulation placed on attic floor when the attic is not used as living space.",
        },
    ],
    "windows_shading": [
        {
            "id": "efficient_glazing",
            "label": "Efficient glazing and profiles",
            "description": "Double/triple glazing and insulated frames to improve comfort and reduce heat loss.",
        },
        {
            "id": "external_shading",
            "label": "External shading",
            "description": "External shading to reduce summer overheating and solar gains.",
        },
    ],
    "hvac_services": [
        {
            "id": "centralised_service_concept",
            "label": "Centralised service concept",
            "description": "Centralized DHW or heating station with easier optimization and maintenance.",
        },
        {
            "id": "decentralised_service_concept",
            "label": "Decentralised service concept",
            "description": "Separate supply per apartment or unit with less piping but more maintenance points.",
        },
    ],
    "solar_integration": [
        {
            "id": "facade_pv",
            "label": "Facade photovoltaic integration",
            "description": "PV modules integrated into facade areas where orientation and shading allow.",
        },
        {
            "id": "solar_thermal_collectors",
            "label": "Solar thermal collectors",
            "description": "Solar thermal collectors integrated into roof or facade surfaces.",
        },
    ],
}


JUSTIFICATIONS = {
    "external_insulation": [
        {
            "id": "building_envelope_solution_booklet",
            "label": "Building Envelope Retrofit Solution Booklet",
            "type": "source",
            "note": "Explains external insulation, thermal bridges, and comfort benefits.",
        }
    ],
    "internal_insulation": [
        {
            "id": "building_envelope_solution_booklet",
            "label": "Building Envelope Retrofit Solution Booklet",
            "type": "source",
            "note": "Lists internal insulation drawbacks and building-physics risks.",
        }
    ],
    "roof_attic": [
        {
            "id": "building_envelope_solution_booklet",
            "label": "Building Envelope Retrofit Solution Booklet",
            "type": "source",
            "note": "Describes roof insulation, attic options, and vapour barrier placement.",
        }
    ],
    "windows_shading": [
        {
            "id": "retrofit_strategies_design_guide",
            "label": "Retrofit Strategies Design Guide",
            "type": "source",
            "note": "Discusses windows, shading, and summer overheating prevention.",
        }
    ],
    "hvac_services": [
        {
            "id": "retrofit_strategies_design_guide",
            "label": "Retrofit Strategies Design Guide",
            "type": "source",
            "note": "Discusses HVAC and service module renewal concepts.",
        }
    ],
    "solar_integration": [
        {
            "id": "retrofit_strategies_design_guide",
            "label": "Retrofit Strategies Design Guide",
            "type": "source",
            "note": "Discusses active solar integration, orientation, and shading effects.",
        }
    ],
}


SYNERGIES = {
    "external_insulation": ["roof_attic", "windows_shading"],
    "roof_attic": ["external_insulation"],
    "windows_shading": ["external_insulation", "solar_integration"],
    "solar_integration": ["windows_shading"],
    "hvac_services": ["building_envelope"],
}


def infer_strategy(query: str) -> str:
    query_lower = query.lower()
    scores = {}
    for strategy, data in STRATEGIES.items():
        score = sum(
            max(1, len(keyword.split()))
            for keyword in data["keywords"]
            if keyword in query_lower
        )
        if score:
            scores[strategy] = score
    if scores:
        return max(scores.items(), key=lambda item: item[1])[0]
    return "building_envelope"


def graph_context_for_strategy(strategy: str) -> dict:
    if strategy not in STRATEGIES:
        strategy = "building_envelope"

    nodes = [
        {
            "id": strategy,
            "type": "strategy",
            "label": STRATEGIES[strategy]["label"],
        }
    ]
    edges = []
    literature_sources = []
    design_options = []

    for option in DESIGN_OPTIONS.get(strategy, []):
        nodes.append({"type": "design_option", **option})
        design_options.append(option["id"])
        edges.append(
            {
                "source": strategy,
                "target": option["id"],
                "relation": "has_variant",
            }
        )

    for source in JUSTIFICATIONS.get(strategy, []):
        nodes.append(source)
        literature_sources.append(source["id"])
        edges.append(
            {
                "source": strategy,
                "target": source["id"],
                "relation": "justified_by",
                "note": source.get("note", ""),
            }
        )

    synergies = SYNERGIES.get(strategy, [])
    for synergy in synergies:
        if synergy in STRATEGIES:
            nodes.append(
                {
                    "id": synergy,
                    "type": "strategy",
                    "label": STRATEGIES[synergy]["label"],
                }
            )
            edges.append(
                {
                    "source": strategy,
                    "target": synergy,
                    "relation": "synergy_with",
                }
            )

    return {
        "strategy": strategy,
        "nodes": nodes,
        "edges": edges,
        "literature_sources": literature_sources,
        "design_options": design_options,
        "synergies": synergies,
    }


def strategy_keywords(strategy: str) -> list[str]:
    keywords = list(STRATEGIES.get(strategy, {}).get("keywords", []))
    for option in DESIGN_OPTIONS.get(strategy, []):
        keywords.extend(option["label"].lower().split())
    for source in JUSTIFICATIONS.get(strategy, []):
        keywords.extend(source["label"].lower().split())
    return sorted(set(keywords))
