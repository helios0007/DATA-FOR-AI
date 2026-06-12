"""
Stage 5 — LLM Recommendation Generation with GraphRAG
Retrieves knowledge context from graph + ChromaDB, then calls the
Anthropic API to generate geometric recommendations per strategy.
"""

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import networkx as nx
from networkx.readwrite import json_graph

from src import llm_client
from src.context_enricher import SiteContext
from src.ifc_parser import BuildingFeatures
from src.strategy_scorer import StrategyScore
from src.thermal_diagnosis import ThermalDiagnosis
from src.utils import resolve_path

GRAPH_PATH  = "graph/strategy_graph.json"
CHROMA_PATH = "graph/chroma_db"
COLLECTION  = "passive_design_knowledge"
EMBED_MODEL = "all-MiniLM-L6-v2"
MAX_TOKENS  = 1000
N_RESULTS   = 5


# ── Output data class ─────────────────────────────────────────────────────────

@dataclass
class FinalReport:
    metadata: dict
    building_summary: dict
    site_summary: dict
    diagnosis_summary: dict
    strategies: list[dict]   # includes LLM recommendation text
    generated_at: str


# ── Graph loading ─────────────────────────────────────────────────────────────

@lru_cache(maxsize=2)
def load_graph(path: str = GRAPH_PATH) -> nx.DiGraph:
    with open(resolve_path(path), encoding="utf-8") as f:
        data = json.load(f)
    return json_graph.node_link_graph(data, directed=True)


@lru_cache(maxsize=1)
def load_embed_model(name: str = EMBED_MODEL):
    """
    Loading the sentence-transformer takes several seconds — do it once.
    Returns None when sentence-transformers isn't installed (RAG optional).
    """
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return None
    return SentenceTransformer(name)


@lru_cache(maxsize=1)
def load_chroma_collection(path: str = CHROMA_PATH, name: str = COLLECTION):
    """
    Returns the ChromaDB collection, or None if chromadb isn't installed
    or the store hasn't been built — recommendations then run without RAG.
    """
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(resolve_path(path)))
        return client.get_collection(name)
    except Exception:
        return None


# ── GraphRAG retrieval ────────────────────────────────────────────────────────

def retrieve_for_strategy(
    strategy_name: str,
    graph: nx.DiGraph,
    collection,
    embed_model,
    n_results: int = N_RESULTS,
) -> str:
    """
    1. Walk graph from strategy node to collect justified_by, has_variant, synergy_with edges.
    2. Query ChromaDB for literature passages relevant to this strategy.
    3. Return formatted context string for the LLM prompt.
    """
    graph_context: list[str] = []

    if strategy_name in graph:
        for _, neighbor, data in graph.out_edges(strategy_name, data=True):
            node_data = graph.nodes.get(neighbor, {})
            relation  = data.get("relation", "")

            if relation == "justified_by":
                graph_context.append(
                    f"Justified by {node_data.get('label', neighbor)}: {data.get('note', '')}"
                )
            elif relation == "has_variant":
                desc = node_data.get("description", "")
                perf = node_data.get("performance_note", "")
                graph_context.append(
                    f"Design option: {node_data.get('label', neighbor)} — {desc} {perf}"
                )
            elif relation == "synergy_with":
                graph_context.append(
                    f"Synergy with {neighbor}: {data.get('note', '')}"
                )

    # Vector retrieval from ChromaDB
    query = f"{strategy_name} passive cooling Barcelona Mediterranean climate"
    try:
        results = collection.query(
            query_embeddings=[embed_model.encode(query).tolist()],
            n_results=n_results,
            where={"strategy": {"$in": [strategy_name, "general"]}},
        )
        doc_context = "\n---\n".join(results["documents"][0]) if results["documents"] else ""
    except Exception:
        doc_context = ""

    return (
        "KNOWLEDGE GRAPH CONTEXT:\n" + "\n".join(graph_context)
        + "\n\nLITERATURE CONTEXT:\n" + doc_context
    )


# ── Prompt templates ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a passive building design advisor specialising in
Mediterranean climates, specifically Barcelona, Spain. You help architects
improve thermal comfort in the design phase of new buildings.

Your role is to generate specific, geometric, actionable recommendations that
reference the architect's actual building model elements by their IFC element IDs.

Rules:
1. Always reference specific IFC element IDs when describing changes needed
2. Always cite the literature source that justifies each recommendation
3. Always provide 2–3 design options (not just one) with brief pros/cons
4. Be quantitative where possible: give dimensions, ratios, depths, areas
5. Acknowledge limitations honestly — if Barcelona's climate limits the
   effectiveness of a strategy (e.g. night purge), say so explicitly
6. Keep each recommendation to 250–350 words
7. Do not recommend active mechanical systems — passive design only
8. Do not assess regulatory compliance or issue certifications"""


def build_recommendation_prompt(
    score: StrategyScore,
    building: BuildingFeatures,
    context: SiteContext,
    diagnosis: ThermalDiagnosis,
    retrieved_context: str,
    all_scores: list[StrategyScore],
) -> str:
    synergy_strategies = [
        s.strategy_name for s in all_scores
        if s.strategy_name != score.strategy_name
        and s.impact_level in ("HIGH", "MEDIUM")
        and s.precondition_met != "NO"
    ]

    dominant_mass = (
        building.facades[0].construction_mass if building.facades else "medium"
    )

    return f"""
BUILDING CONTEXT:
- IFC file: {building.ifc_file_path}
- Building use: {building.building_use}
- Total floor area: {building.total_floor_area_m2:.0f} m²
- Floors: {building.number_of_floors}
- Floor-to-ceiling height: {building.floor_to_ceiling_height_m:.1f} m
- Building depth: {building.building_depth_m:.1f} m
- Dominant construction: {dominant_mass}

SITE CONTEXT:
- Thermal comfort zone: {context.thermal_comfort_gridcode} ({context.thermal_comfort_label})
- Sky view factor: {context.svf_mean:.2f}
- Canyon H/W ratio: {context.canyon_hw_ratio:.1f}
- Canyon wind correction: {context.canyon_wind_correction}
- Summer mean wind speed (EPW): {context.summer_mean_wind_m_s:.1f} m/s
- Canyon-corrected wind: {context.summer_mean_wind_m_s * context.canyon_wind_correction:.1f} m/s
- July diurnal swing: {context.july_diurnal_swing_C:.1f}°C
- Summer CDH above 26°C: {context.summer_CDH_above_26C:.0f}

THERMAL DIAGNOSIS:
- Overheating risk: {diagnosis.overheating_risk_level}
- Proxy ODH: {diagnosis.estimated_proxy_ODH:.2f}
- Critical facades (element IDs): {', '.join(diagnosis.critical_facades)}

STRATEGY TO RECOMMEND: {score.strategy_name.upper().replace('_', ' ')}
- Impact score: {score.impact_score:.0f}/100
- Impact level: {score.impact_level}
- Precondition: {score.precondition_met} — {score.precondition_reason}
- Affected IFC elements: {', '.join(score.affected_element_ids[:6])}
- Key driver factor: {score.key_driver}
- Factor breakdown: {json.dumps(score.factor_scores, indent=2)}

OTHER VIABLE STRATEGIES (for synergy mentions):
{', '.join(synergy_strategies) if synergy_strategies else 'none'}

RETRIEVED KNOWLEDGE:
{retrieved_context}

TASK:
Write a recommendation for implementing {score.strategy_name.replace('_', ' ')} on this
specific building. Structure your response as follows:

1. WHY THIS STRATEGY (2–3 sentences, cite the key driver factor and its value,
   reference the relevant standard or paper from the retrieved context)

2. AFFECTED ELEMENTS (list the IFC element IDs and what each represents)

3. DESIGN OPTIONS (2–3 options with:
   - name and brief description
   - specific dimensions or parameters for this building
   - pros and cons for this specific site)

4. GEOMETRIC CHANGES REQUIRED (specific instructions referencing element IDs,
   include dimensions where possible)

5. EXPECTED BENEFIT (quantified estimate of ODH reduction based on literature,
   acknowledge any limitations for Barcelona's specific climate)

6. SYNERGIES (if applicable, mention how this strategy combines with
   {', '.join(synergy_strategies[:2]) if synergy_strategies else 'other strategies'})
"""


# ── Anthropic API call ────────────────────────────────────────────────────────

def generate_recommendation(
    score: StrategyScore,
    building: BuildingFeatures,
    context: SiteContext,
    diagnosis: ThermalDiagnosis,
    retrieved_context: str,
    all_scores: list[StrategyScore],
) -> str:
    prompt = build_recommendation_prompt(
        score, building, context, diagnosis, retrieved_context, all_scores
    )
    return llm_client.complete(
        SYSTEM_PROMPT,
        [{"role": "user", "content": prompt}],
        max_tokens=MAX_TOKENS,
    )


# ── Report assembly ───────────────────────────────────────────────────────────

def generate_report(
    building: BuildingFeatures,
    context: SiteContext,
    diagnosis: ThermalDiagnosis,
    ranked_scores: list[StrategyScore],
    skip_llm: bool = False,
) -> FinalReport:
    """
    Load graph + RAG, generate LLM recommendations for all viable strategies,
    and assemble the final report dataclass.
    """
    # Knowledge base (cached at module level — loaded once per process)
    graph = load_graph()
    embed_model = load_embed_model()
    collection = load_chroma_collection()

    def build_strategy_entry(rank: int, score: StrategyScore) -> dict:
        # Retrieve context from graph + vector store
        if collection is not None:
            retrieved = retrieve_for_strategy(score.strategy_name, graph, collection, embed_model)
        else:
            retrieved = "(RAG store not available — run build_rag.py first)"

        # Only call LLM for viable strategies
        if score.precondition_met != "NO" and not skip_llm:
            try:
                rec_text = generate_recommendation(
                    score, building, context, diagnosis, retrieved, ranked_scores
                )
            except Exception as e:
                rec_text = f"(LLM unavailable: {e})"
        elif score.precondition_met == "NO":
            rec_text = f"Strategy excluded: {score.precondition_reason}"
        else:
            rec_text = "(LLM recommendations skipped — run without --skip-llm once API key is active)"

        return {
            "rank": rank,
            "name": score.strategy_name,
            "precondition_met": score.precondition_met,
            "precondition_reason": score.precondition_reason,
            "impact_score": score.impact_score,
            "impact_level": score.impact_level,
            "affected_elements": score.affected_element_ids,
            "key_driver": score.key_driver,
            "factor_scores": score.factor_scores,
            "recommendation": rec_text,
        }

    # The per-strategy LLM calls are independent — run them concurrently
    # (sequentially this was ~5 × full LLM latency per report).
    with ThreadPoolExecutor(max_workers=len(ranked_scores) or 1) as pool:
        strategies_output = list(
            pool.map(
                lambda rs: build_strategy_entry(*rs),
                enumerate(ranked_scores, start=1),
            )
        )

    ifc_name = Path(building.ifc_file_path).name
    dominant_mass = building.facades[0].construction_mass if building.facades else "medium"

    return FinalReport(
        metadata={
            "ifc_file": ifc_name,
            "site_lat": building.site_latitude,
            "site_lon": building.site_longitude,
            "thermal_comfort_zone": context.thermal_comfort_gridcode,
            "overheating_risk": diagnosis.overheating_risk_level,
            "proxy_odh": diagnosis.estimated_proxy_ODH,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        building_summary={
            "total_floor_area_m2": building.total_floor_area_m2,
            "number_of_floors": building.number_of_floors,
            "floor_to_ceiling_height_m": building.floor_to_ceiling_height_m,
            "building_depth_m": building.building_depth_m,
            "dominant_construction_mass": dominant_mass,
            "has_opposing_openings": building.has_opposing_openings,
        },
        site_summary={
            "thermal_comfort_label": context.thermal_comfort_label,
            "svf_mean": context.svf_mean,
            "canyon_hw_ratio": context.canyon_hw_ratio,
            "dominant_wind_direction": context.dominant_wind_direction,
            "summer_mean_wind_m_s": context.summer_mean_wind_m_s,
            "july_diurnal_swing_C": context.july_diurnal_swing_C,
            "summer_CDH_above_26C": context.summer_CDH_above_26C,
        },
        diagnosis_summary={
            "risk_level": diagnosis.overheating_risk_level,
            "proxy_odh": diagnosis.estimated_proxy_ODH,
            "critical_facades": diagnosis.critical_facades,
            "ventilation_deficit": diagnosis.ventilation_deficit,
            "night_purge_viable": diagnosis.night_purge_viable,
            "diagnosis_text": diagnosis.diagnosis_text,
        },
        strategies=strategies_output,
        generated_at=datetime.now().isoformat(timespec="seconds"),
    )
