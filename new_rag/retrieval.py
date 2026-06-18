from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from config import (
    COLLECTION_NAME,
    DEFAULT_BM25_K,
    DEFAULT_CHUNKS_PATH,
    DEFAULT_TOP_K,
    DEFAULT_VECTOR_K,
    VECTOR_DB_DIR,
)
from strategy_graph import graph_context_for_strategy, infer_strategy, strategy_keywords


STOPWORDS = {
    "a",
    "about",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "should",
    "the",
    "these",
    "this",
    "to",
    "what",
    "when",
    "where",
    "which",
    "why",
    "with",
}


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-zA-Z0-9]+(?:[-_/][a-zA-Z0-9]+)?", text.lower())
        if len(token) > 1 and token not in STOPWORDS
    ]


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def normalize_chunk(raw: dict) -> dict:
    metadata = raw.get("metadata", {})
    return {
        "id": raw.get("id", ""),
        "text": raw.get("text", ""),
        "metadata": {
            "source": metadata.get("source", raw.get("source", "")),
            "source_id": metadata.get("source_id", raw.get("source_id", "")),
            "source_title": metadata.get("source_title", raw.get("source", "")),
            "page": metadata.get("page", raw.get("page", "")),
            "chunk_index": metadata.get("chunk_index", raw.get("chunk_index", 0)),
            "citation": metadata.get("citation", raw.get("citation", "")),
        },
    }


def load_chunks(path: Path = DEFAULT_CHUNKS_PATH) -> list[dict]:
    return [normalize_chunk(record) for record in read_jsonl(path)]


def chunk_key(chunk: dict) -> tuple[str, str, str]:
    metadata = chunk["metadata"]
    return (
        str(metadata.get("source", "")),
        str(metadata.get("page", "")),
        str(metadata.get("chunk_index", "")),
    )


def build_idf(chunks: list[dict]) -> dict[str, float]:
    frequencies = Counter()
    for chunk in chunks:
        frequencies.update(set(tokenize(chunk["text"])))
    total = max(len(chunks), 1)
    return {
        token: math.log((total + 1) / (frequency + 1)) + 1.0
        for token, frequency in frequencies.items()
    }


def bm25_scores(query_terms: list[str], chunks: list[dict], idf: dict[str, float]) -> list[dict]:
    avg_len = sum(len(tokenize(chunk["text"])) for chunk in chunks) / max(len(chunks), 1)
    k1 = 1.5
    b = 0.75
    query_counts = Counter(query_terms)
    scored = []

    for chunk in chunks:
        terms = tokenize(chunk["text"])
        counts = Counter(terms)
        doc_len = max(len(terms), 1)
        score = 0.0
        for term, query_count in query_counts.items():
            tf = counts.get(term, 0)
            if not tf:
                continue
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / max(avg_len, 1))
            score += idf.get(term, 1.0) * numerator / denominator * query_count
        if score > 0:
            scored.append({**chunk, "bm25_score": score})

    return sorted(scored, key=lambda item: item["bm25_score"], reverse=True)


def vector_retrieve(query: str, n_results: int) -> list[dict]:
    try:
        import chromadb
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

        client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
        collection = client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=DefaultEmbeddingFunction(),
        )
        results = collection.query(query_texts=[query], n_results=n_results)
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        chunks = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            chunks.append(
                {
                    "id": f"{metadata.get('source', '')}:page-{metadata.get('page', '')}:chunk-{metadata.get('chunk_index', '')}",
                    "text": document,
                    "metadata": metadata,
                    "vector_distance": distance,
                }
            )
        return chunks
    except Exception:
        return []


def strategy_filter_score(strategy: str, chunk: dict) -> float:
    text = chunk["text"].lower()
    metadata_text = " ".join(str(value) for value in chunk["metadata"].values()).lower()
    haystack = f"{text} {metadata_text}"
    keywords = strategy_keywords(strategy)
    hits = sum(1 for keyword in keywords if keyword and keyword in haystack)
    return min(hits / 5.0, 1.0)


def graph_boost_score(graph_context: dict, chunk: dict) -> float:
    haystack = f"{chunk['text']} {' '.join(str(value) for value in chunk['metadata'].values())}".lower()
    terms = []
    for node in graph_context.get("nodes", []):
        terms.append(str(node.get("id", "")).replace("_", " "))
        terms.append(str(node.get("label", "")))
    hits = sum(1 for term in terms if term and term.lower() in haystack)
    return min(hits / 4.0, 1.0)


def merge_candidates(vector_candidates: list[dict], bm25_candidates: list[dict]) -> list[dict]:
    merged = {}
    for rank, chunk in enumerate(vector_candidates, start=1):
        merged[chunk_key(chunk)] = {
            **chunk,
            "vector_rank": rank,
            "bm25_rank": None,
            "bm25_score": 0.0,
        }
    for rank, chunk in enumerate(bm25_candidates, start=1):
        key = chunk_key(chunk)
        if key not in merged:
            merged[key] = {
                **chunk,
                "vector_rank": None,
                "vector_distance": None,
                "bm25_rank": rank,
                "bm25_score": chunk.get("bm25_score", 0.0),
            }
        else:
            merged[key]["bm25_rank"] = rank
            merged[key]["bm25_score"] = chunk.get("bm25_score", 0.0)
    return list(merged.values())


def reciprocal_rank(rank: int | None) -> float:
    if rank is None:
        return 0.0
    return 1.0 / (rank + 1)


def rerank(query: str, strategy: str, graph_context: dict, candidates: list[dict]) -> list[dict]:
    query_terms = set(tokenize(query))
    max_bm25 = max((candidate.get("bm25_score", 0.0) for candidate in candidates), default=1.0)

    for candidate in candidates:
        text = candidate["text"].lower()
        coverage = (
            len([term for term in query_terms if term in text]) / max(len(query_terms), 1)
        )
        bm25_component = candidate.get("bm25_score", 0.0) / max(max_bm25, 1.0)
        strategy_component = strategy_filter_score(strategy, candidate)
        graph_component = graph_boost_score(graph_context, candidate)
        vector_component = reciprocal_rank(candidate.get("vector_rank"))
        bm25_rank_component = reciprocal_rank(candidate.get("bm25_rank"))

        candidate["score"] = round(
            0.25 * vector_component
            + 0.25 * bm25_rank_component
            + 0.20 * bm25_component
            + 0.15 * strategy_component
            + 0.10 * graph_component
            + 0.05 * coverage,
            5,
        )
    return sorted(candidates, key=lambda item: item["score"], reverse=True)


def assess_sufficiency(strategy: str, graph_context: dict, chunks: list[dict]) -> dict:
    if not chunks:
        return {
            "sufficient": False,
            "reason": "No chunks were retrieved.",
        }
    has_graph = bool(graph_context.get("nodes")) and bool(graph_context.get("edges"))
    has_source = any(chunk["metadata"].get("source_title") for chunk in chunks)
    has_strategy_evidence = max(strategy_filter_score(strategy, chunk) for chunk in chunks) > 0
    sufficient = has_graph and has_source and has_strategy_evidence
    return {
        "sufficient": sufficient,
        "has_graph_context": has_graph,
        "has_source_evidence": has_source,
        "has_strategy_evidence": has_strategy_evidence,
        "reason": (
            "Graph and literature evidence are present."
            if sufficient
            else "Context may be missing graph, source, or strategy-specific evidence."
        ),
    }


def retrieve_new_rag(
    query: str,
    chunks_path: Path = DEFAULT_CHUNKS_PATH,
    top_k: int = DEFAULT_TOP_K,
    vector_k: int = DEFAULT_VECTOR_K,
    bm25_k: int = DEFAULT_BM25_K,
) -> dict:
    strategy = infer_strategy(query)
    graph_context = graph_context_for_strategy(strategy)
    graph_terms = " ".join(
        [
            strategy,
            " ".join(strategy_keywords(strategy)),
            " ".join(graph_context.get("literature_sources", [])),
        ]
    )
    retrieval_query = f"{query} {graph_terms}"

    chunks = load_chunks(chunks_path)
    idf = build_idf(chunks)
    bm25_candidates = bm25_scores(tokenize(retrieval_query), chunks, idf)[:bm25_k]
    vector_candidates = vector_retrieve(retrieval_query, vector_k)

    candidates = merge_candidates(vector_candidates, bm25_candidates)
    ranked = rerank(retrieval_query, strategy, graph_context, candidates)
    final_chunks = ranked[:top_k]
    sufficiency = assess_sufficiency(strategy, graph_context, final_chunks)

    return {
        "question": query,
        "strategy": strategy,
        "graph_context": graph_context,
        "retrieved_chunks": final_chunks,
        "sufficiency": sufficiency,
    }
