from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from chunker import chunk_pages
from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DEFAULT_CHUNKS_PATH,
    DEFAULT_TOP_K,
    NEW_RAG_DIR,
    PAGES_JSONL,
    RAW_PDF_DIR,
)
from document_loader import extract_pdf_pages, write_jsonl
from index_builder import index_chunks
from retrieval import retrieve_new_rag
from source_catalog import discover_sources


DEFAULT_QUESTIONS_PATH = Path(__file__).with_name("sample_questions.json")
DEFAULT_EVAL_QUESTIONS_PATH = Path(__file__).with_name("eval_questions.json")
DEFAULT_EVAL_OUTPUT_PATH = NEW_RAG_DIR / "data" / "eval_runs" / "rag_outputs.json"


def load_questions(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def source_titles(result: dict) -> set[str]:
    return {
        chunk["metadata"].get("source_title", "")
        for chunk in result["retrieved_chunks"]
        if chunk["metadata"].get("source_title")
    }


def evaluate_case(case: dict, result: dict) -> dict:
    expected_sources = set(case.get("expected_source_titles", []))
    actual_sources = source_titles(result)
    strategy_ok = result["strategy"] == case.get("expected_strategy")
    sources_ok = not expected_sources or bool(expected_sources & actual_sources)
    sufficient_ok = bool(result["sufficiency"].get("sufficient"))
    passed = strategy_ok and sources_ok and sufficient_ok

    return {
        "id": case.get("id", ""),
        "question": case["question"],
        "passed": passed,
        "strategy_ok": strategy_ok,
        "sources_ok": sources_ok,
        "sufficient_ok": sufficient_ok,
        "expected_strategy": case.get("expected_strategy"),
        "actual_strategy": result["strategy"],
        "expected_sources": sorted(expected_sources),
        "actual_sources": sorted(actual_sources),
        "top_chunks": [
            {
                "source_title": chunk["metadata"].get("source_title", ""),
                "page": chunk["metadata"].get("page", ""),
                "score": chunk.get("score", 0.0),
                "vector_rank": chunk.get("vector_rank"),
                "bm25_rank": chunk.get("bm25_rank"),
            }
            for chunk in result["retrieved_chunks"][:3]
        ],
    }


def print_test_report(records: list[dict]) -> None:
    passed = sum(1 for record in records if record["passed"])
    print(f"New RAG test: {passed}/{len(records)} passed")
    print("Mechanism: graph strategy inference + BM25 + Chroma vector + graph boost + reranker")
    print()

    for index, record in enumerate(records, start=1):
        status = "PASS" if record["passed"] else "FAIL"
        print(f"{index}. {status} | {record['id']}")
        print(f"   Strategy: {record['actual_strategy']} | expected: {record['expected_strategy']}")
        print(f"   Sources: {', '.join(record['actual_sources'])}")
        for chunk in record["top_chunks"]:
            print(
                "   - "
                f"{chunk['source_title']} p.{chunk['page']} "
                f"score={chunk['score']:.4f} "
                f"vector={chunk['vector_rank'] or '-'} "
                f"bm25={chunk['bm25_rank'] or '-'}"
            )
        print()


def build_draft_answer(result: dict) -> str:
    strategy_label = result["graph_context"]["nodes"][0]["label"]
    chunks = result["retrieved_chunks"]
    if not chunks:
        return "Not enough information was retrieved to answer from the literature."

    source_refs = []
    for chunk in chunks[:3]:
        metadata = chunk["metadata"]
        source_refs.append(f"{metadata.get('source_title', 'source')}, page {metadata.get('page', '')}")
    unique_refs = []
    for ref in source_refs:
        if ref not in unique_refs:
            unique_refs.append(ref)

    return (
        f"Retrieved evidence supports the strategy area: {strategy_label}. "
        f"Use the retrieved literature chunks to write the final recommendation. "
        f"Key evidence sources: {'; '.join(unique_refs)}."
    )


def print_result(result: dict, show_text: bool) -> None:
    print(f"Question: {result['question']}")
    print(f"Strategy: {result['strategy']}")
    print(
        "Graph nodes: "
        + ", ".join(node["id"] for node in result["graph_context"].get("nodes", []))
    )
    print(
        "Graph relations: "
        + ", ".join(edge["relation"] for edge in result["graph_context"].get("edges", []))
    )
    print(f"Sufficiency: {result['sufficiency']['sufficient']} | {result['sufficiency']['reason']}")
    print("\nRetrieved chunks:\n")
    for index, chunk in enumerate(result["retrieved_chunks"], start=1):
        metadata = chunk["metadata"]
        print(
            f"{index}. {metadata.get('source_title', '')} | page {metadata.get('page', '')} | "
            f"score={chunk.get('score', 0):.4f} | "
            f"vector_rank={chunk.get('vector_rank') or '-'} | bm25_rank={chunk.get('bm25_rank') or '-'}"
        )
        if show_text:
            print(f"   {chunk['text'][:700]}...\n")


def eval_output(result: dict) -> dict:
    return {
        "id": "manual_test",
        "answer": build_draft_answer(result),
        "retrieved_chunks": [
            {
                "text": chunk["text"],
                "metadata": {
                    "source_title": chunk["metadata"].get("source_title", ""),
                    "source_id": chunk["metadata"].get("source_id", ""),
                    "page": chunk["metadata"].get("page", ""),
                },
                "score": chunk.get("score", 0.0),
            }
            for chunk in result["retrieved_chunks"]
        ],
        "graph_context": result["graph_context"],
        "sufficiency": result["sufficiency"],
    }


def run_ingest(args: argparse.Namespace) -> None:
    sources = discover_sources(args.raw_pdf_dir)
    if not sources:
        raise SystemExit(f"No PDFs found in {args.raw_pdf_dir}")

    pages = []
    for source in sources:
        source_pages = extract_pdf_pages(source)
        pages.extend(source_pages)
        print(f"Loaded {len(source_pages)} pages from {source['source_title']}")

    chunks = chunk_pages(pages, chunk_size=args.chunk_size, overlap=args.overlap)
    write_jsonl(pages, args.pages_out)
    write_jsonl(chunks, args.chunks_out)

    print(f"Wrote {len(pages)} pages to {args.pages_out}")
    print(f"Wrote {len(chunks)} chunks to {args.chunks_out}")


def run_index(args: argparse.Namespace) -> None:
    count = index_chunks(args.chunks, reset=not args.no_reset)
    print(f"Indexed {count} chunks")


def run_test(args: argparse.Namespace) -> None:
    cases = load_questions(args.questions)
    records = []
    for case in cases:
        result = retrieve_new_rag(case["question"], chunks_path=args.chunks, top_k=args.top_k)
        records.append(evaluate_case(case, result))

    if args.json:
        print(json.dumps(records, indent=2, ensure_ascii=False))
    else:
        print_test_report(records)

    if any(not record["passed"] for record in records):
        raise SystemExit(1)


def run_export_eval(args: argparse.Namespace) -> None:
    cases = load_questions(args.questions)
    outputs = []
    for case in cases:
        result = retrieve_new_rag(case["question"], chunks_path=args.chunks, top_k=args.top_k)
        output = eval_output(result)
        output["id"] = case["id"]
        output["question"] = case["question"]
        outputs.append(output)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(outputs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(outputs)} RAG eval outputs to {args.output}")


def run_ask(args: argparse.Namespace) -> None:
    question = " ".join(args.question).strip()
    if not question:
        question = input("Question: ").strip()
    if not question:
        raise SystemExit("Please provide a question.")

    result = retrieve_new_rag(question, chunks_path=args.chunks, top_k=args.top_k)
    if args.json:
        print(json.dumps(eval_output(result), indent=2, ensure_ascii=False))
    else:
        print_result(result, args.show_text)


def run_all(args: argparse.Namespace) -> None:
    ingest_args = argparse.Namespace(
        raw_pdf_dir=args.raw_pdf_dir,
        pages_out=PAGES_JSONL,
        chunks_out=DEFAULT_CHUNKS_PATH,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    index_args = argparse.Namespace(chunks=DEFAULT_CHUNKS_PATH, no_reset=False)
    test_args = argparse.Namespace(
        questions=DEFAULT_QUESTIONS_PATH,
        chunks=DEFAULT_CHUNKS_PATH,
        top_k=DEFAULT_TOP_K,
        json=False,
    )
    run_ingest(ingest_args)
    run_index(index_args)
    run_test(test_args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Main CLI for the new GraphRAG retriever.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest = subparsers.add_parser("ingest", help="Extract PDFs and create chunks.")
    ingest.add_argument("--raw-pdf-dir", type=Path, default=RAW_PDF_DIR)
    ingest.add_argument("--pages-out", type=Path, default=PAGES_JSONL)
    ingest.add_argument("--chunks-out", type=Path, default=DEFAULT_CHUNKS_PATH)
    ingest.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    ingest.add_argument("--overlap", type=int, default=CHUNK_OVERLAP)
    ingest.set_defaults(func=run_ingest)

    index = subparsers.add_parser("index", help="Build the Chroma vector index.")
    index.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    index.add_argument("--no-reset", action="store_true")
    index.set_defaults(func=run_index)

    test = subparsers.add_parser("test", help="Run retrieval tests.")
    test.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    test.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    test.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    test.add_argument("--json", action="store_true")
    test.set_defaults(func=run_test)

    export_eval = subparsers.add_parser(
        "export-eval",
        help="Export eva_engine-compatible RAG outputs.",
    )
    export_eval.add_argument("--questions", type=Path, default=DEFAULT_EVAL_QUESTIONS_PATH)
    export_eval.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    export_eval.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    export_eval.add_argument("--output", type=Path, default=DEFAULT_EVAL_OUTPUT_PATH)
    export_eval.set_defaults(func=run_export_eval)

    ask = subparsers.add_parser("ask", help="Retrieve evidence for one question.")
    ask.add_argument("question", nargs="*")
    ask.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    ask.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    ask.add_argument("--show-text", action="store_true")
    ask.add_argument("--json", action="store_true")
    ask.set_defaults(func=run_ask)

    run_all_parser = subparsers.add_parser("all", help="Run ingest, index, and test.")
    run_all_parser.add_argument("--raw-pdf-dir", type=Path, default=RAW_PDF_DIR)
    run_all_parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    run_all_parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP)
    run_all_parser.set_defaults(func=run_all)

    return parser


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = build_parser().parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
