import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_QUESTIONS_PATH = Path(__file__).resolve().parent / "sample_eval_questions.json"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "runs"

JUDGE_SYSTEM_INSTRUCTIONS = """You are a strict RAG evaluation judge.
Evaluate only the provided question, expected rubric, retrieved context, and answer.
Do not use outside knowledge.
Return valid JSON only, without markdown fences."""

JUDGE_KEYS = [
    "context_relevance",
    "context_sufficiency",
    "answer_relevance",
    "faithfulness",
    "citation_quality",
    "overall",
]


def load_dotenv(path: Path, override: bool = False) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if override:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower()).strip()


def term_found(term: str, text: str) -> bool:
    return normalize_text(term) in normalize_text(text)


def load_json_or_jsonl(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return []
    if text.startswith("["):
        return json.loads(text)
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def get_page(metadata: dict) -> int:
    try:
        return int(metadata.get("page", -1))
    except (TypeError, ValueError):
        return -1


def source_hit(expected_source: dict, chunks: list[dict], page_window: int) -> bool:
    expected_title = expected_source["source_title"]
    expected_pages = [int(page) for page in expected_source.get("pages", [])]

    for chunk in chunks:
        metadata = chunk.get("metadata", {})
        if metadata.get("source_title") != expected_title:
            continue
        if not expected_pages:
            return True
        page = get_page(metadata)
        if any(abs(page - expected_page) <= page_window for expected_page in expected_pages):
            return True
    return False


def evaluate_retrieval(item: dict, chunks: list[dict], page_window: int) -> dict:
    expected_sources = item.get("expected_sources", [])
    hits = [source_hit(source, chunks, page_window) for source in expected_sources]

    return {
        "expected_source_count": len(expected_sources),
        "expected_source_hits": sum(1 for hit in hits if hit),
        "expected_sources_found": all(hits) if expected_sources else True,
        "top_chunks": [
            {
                "rank": index,
                "source_title": chunk.get("metadata", {}).get("source_title", ""),
                "page": chunk.get("metadata", {}).get("page", ""),
                "score": chunk.get("score"),
                "distance": chunk.get("distance"),
            }
            for index, chunk in enumerate(chunks, start=1)
        ],
    }


def evaluate_answer(item: dict, answer: str) -> dict:
    required_terms = item.get("required_answer_terms", [])
    forbidden_terms = item.get("forbidden_answer_terms", [])
    missing_required = [term for term in required_terms if not term_found(term, answer)]
    present_forbidden = [term for term in forbidden_terms if term_found(term, answer)]
    citations = re.findall(r"\[[^\]]+,\s*page\s+\d+\]", answer, flags=re.IGNORECASE)

    return {
        "required_terms_total": len(required_terms),
        "required_terms_found": len(required_terms) - len(missing_required),
        "missing_required_terms": missing_required,
        "present_forbidden_terms": present_forbidden,
        "citation_count": len(citations),
        "citations": citations,
        "answer_checks_passed": not missing_required and not present_forbidden,
    }


def normalize_list(values: list | None) -> set[str]:
    if not values:
        return set()
    return {normalize_text(str(value)) for value in values if str(value).strip()}


def graph_node_ids(graph_context: dict) -> set[str]:
    nodes = graph_context.get("nodes", [])
    ids = set()
    for node in nodes:
        if isinstance(node, dict):
            value = node.get("id") or node.get("name") or node.get("label")
        else:
            value = node
        if value:
            ids.add(normalize_text(str(value)))
    return ids


def graph_relations(graph_context: dict) -> set[str]:
    edges = graph_context.get("edges", [])
    relations = set()
    for edge in edges:
        if isinstance(edge, dict):
            value = edge.get("relation") or edge.get("type") or edge.get("label")
        else:
            value = edge
        if value:
            relations.add(normalize_text(str(value)))
    return relations


def graph_literature_sources(graph_context: dict) -> set[str]:
    sources = set()
    for node in graph_context.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_type = normalize_text(str(node.get("type", "")))
        if node_type in {"paper", "standard", "literature", "source"}:
            value = node.get("id") or node.get("label") or node.get("name")
            if value:
                sources.add(normalize_text(str(value)))
    for source in graph_context.get("literature_sources", []):
        sources.add(normalize_text(str(source)))
    return sources


def evaluate_graph_context(item: dict, rag_result: dict) -> dict | None:
    expected_strategy = item.get("expected_strategy")
    expected_nodes = normalize_list(item.get("expected_graph_nodes"))
    expected_relations = normalize_list(item.get("expected_relations"))
    expected_literature = normalize_list(item.get("expected_literature_sources"))

    if not any([expected_strategy, expected_nodes, expected_relations, expected_literature]):
        return None

    graph_context = rag_result.get("graph_context") or {}
    if not graph_context:
        return {
            "graph_checks_passed": False,
            "expected_strategy_found": not expected_strategy,
            "missing_graph_nodes": sorted(expected_nodes),
            "missing_relations": sorted(expected_relations),
            "missing_literature_sources": sorted(expected_literature),
            "reason": "Expected graph context, but RAG output did not include graph_context.",
        }

    actual_strategy = normalize_text(str(graph_context.get("strategy", "")))
    actual_nodes = graph_node_ids(graph_context)
    actual_relations = graph_relations(graph_context)
    actual_literature = graph_literature_sources(graph_context)

    expected_strategy_found = (
        True if not expected_strategy else normalize_text(str(expected_strategy)) == actual_strategy
    )
    missing_nodes = sorted(expected_nodes - actual_nodes)
    missing_relations = sorted(expected_relations - actual_relations)
    missing_literature = sorted(expected_literature - actual_literature)

    passed = (
        expected_strategy_found
        and not missing_nodes
        and not missing_relations
        and not missing_literature
    )

    return {
        "graph_checks_passed": passed,
        "expected_strategy_found": expected_strategy_found,
        "actual_strategy": graph_context.get("strategy", ""),
        "actual_graph_nodes": sorted(actual_nodes),
        "actual_relations": sorted(actual_relations),
        "actual_literature_sources": sorted(actual_literature),
        "missing_graph_nodes": missing_nodes,
        "missing_relations": missing_relations,
        "missing_literature_sources": missing_literature,
        "reason": "Graph context matched expectations." if passed else "Graph context missed expected items.",
    }


def format_context(chunks: list[dict]) -> str:
    blocks = []
    for index, chunk in enumerate(chunks, start=1):
        metadata = chunk.get("metadata", {})
        blocks.append(
            "\n".join(
                [
                    f"[{index}]",
                    f"Source title: {metadata.get('source_title', '')}",
                    f"Source ID: {metadata.get('source_id', '')}",
                    f"Page: {metadata.get('page', '')}",
                    "Excerpt:",
                    chunk.get("text", ""),
                ]
            )
        )
    return "\n\n".join(blocks)


def expected_sources_text(item: dict) -> str:
    sources = item.get("expected_sources", [])
    if not sources:
        return "No specific expected source."
    lines = []
    for source in sources:
        pages = ", ".join(str(page) for page in source.get("pages", [])) or "any page"
        lines.append(f"- {source['source_title']}, page(s): {pages}")
    return "\n".join(lines)


def build_judge_prompt(item: dict, answer: str, chunks: list[dict], answer_eval: dict) -> str:
    graph_expectations = {
        "expected_strategy": item.get("expected_strategy"),
        "expected_graph_nodes": item.get("expected_graph_nodes", []),
        "expected_relations": item.get("expected_relations", []),
        "expected_literature_sources": item.get("expected_literature_sources", []),
    }
    return f"""Evaluate this RAG result.

Question:
{item["question"]}

Expected source/page targets:
{expected_sources_text(item)}

Required answer concepts:
{", ".join(item.get("required_answer_terms", [])) or "none"}

Forbidden unsupported claims:
{", ".join(item.get("forbidden_answer_terms", [])) or "none"}

Retrieved context:
{format_context(chunks)}

Generated answer:
{answer}

Deterministic checks:
{json.dumps(answer_eval, indent=2, ensure_ascii=False)}

GraphRAG expectations, if any:
{json.dumps(graph_expectations, indent=2, ensure_ascii=False)}

Return JSON with exactly this schema:
{{
  "context_relevance": {{"score": 1, "reason": "..."}},
  "context_sufficiency": {{"score": 1, "reason": "..."}},
  "answer_relevance": {{"score": 1, "reason": "..."}},
  "faithfulness": {{"score": 1, "reason": "..."}},
  "citation_quality": {{"score": 1, "reason": "..."}},
  "overall": {{"score": 1, "reason": "..."}},
  "unsupported_claims": ["..."],
  "missing_expected_points": ["..."],
  "recommended_fix": "..."
}}

Scores use 1=poor, 2=weak, 3=acceptable, 4=good, 5=excellent."""


def openai_text(system_instructions: str, prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing.")
    try:
        from openai import OpenAI
    except ModuleNotFoundError as error:
        raise RuntimeError("The openai package is not installed. Run: pip install openai") from error

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        instructions=system_instructions,
        input=prompt,
    )
    return response.output_text


def gemini_text(system_instructions: str, prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is missing.")
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    if not model.startswith("models/"):
        model = f"models/{model}"
    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"{quote(model, safe='/')}:generateContent?"
        f"{urlencode({'key': api_key})}"
    )
    payload = {
        "systemInstruction": {"parts": [{"text": system_instructions}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini HTTP error {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError("Could not reach Gemini API.") from error
    parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    return "".join(part.get("text", "") for part in parts).strip()


def anthropic_text(system_instructions: str, prompt: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is missing.")
    try:
        from anthropic import Anthropic
    except ModuleNotFoundError as error:
        raise RuntimeError("The anthropic package is not installed. Run: pip install anthropic") from error

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        max_tokens=800,
        system=system_instructions,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()


def ollama_text(system_instructions: str, prompt: str) -> str:
    payload = {
        "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        "prompt": f"{system_instructions}\n\n{prompt}",
        "stream": False,
    }
    request = Request(
        os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate"),
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP error {error.code}: {body}") from error
    except URLError as error:
        raise RuntimeError("Could not reach Ollama.") from error
    return result.get("response", "").strip()


def generate_judge_text(system_instructions: str, prompt: str) -> str:
    provider = os.getenv("JUDGE_PROVIDER", os.getenv("LLM_PROVIDER", "openai")).lower()
    if provider == "chatgpt":
        provider = "openai"
    if provider == "claude":
        provider = "anthropic"

    providers = [provider]
    if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
        providers = ["ollama"]
    elif provider == "gemini" and not os.getenv("GEMINI_API_KEY"):
        providers = ["ollama"]
    elif provider == "anthropic" and not os.getenv("ANTHROPIC_API_KEY"):
        providers = ["ollama"]
    elif provider not in {"openai", "gemini", "anthropic", "ollama"}:
        providers = ["ollama"]
    elif provider != "ollama":
        providers.append("ollama")

    errors = []
    for candidate in providers:
        try:
            if candidate == "openai":
                return openai_text(system_instructions, prompt)
            if candidate == "gemini":
                return gemini_text(system_instructions, prompt)
            if candidate == "anthropic":
                return anthropic_text(system_instructions, prompt)
            if candidate == "ollama":
                return ollama_text(system_instructions, prompt)
        except Exception as error:
            errors.append(f"{candidate}: {error}")
            continue

    raise RuntimeError("All judge providers failed. " + " | ".join(errors))


def extract_json_object(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("judge did not return a JSON object")
    return json.loads(text[start : end + 1])


def normalize_judge(raw_result: dict) -> dict:
    result = {}
    for key in JUDGE_KEYS:
        value = raw_result.get(key, {})
        if not isinstance(value, dict):
            value = {"score": value, "reason": ""}
        try:
            score = int(value.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        result[key] = {
            "score": max(0, min(score, 5)),
            "reason": str(value.get("reason", "")).strip(),
        }
    result["unsupported_claims"] = raw_result.get("unsupported_claims", [])
    result["missing_expected_points"] = raw_result.get("missing_expected_points", [])
    result["recommended_fix"] = str(raw_result.get("recommended_fix", "")).strip()
    return result


def judge_result(item: dict, answer: str, chunks: list[dict], answer_eval: dict) -> dict:
    prompt = build_judge_prompt(item, answer, chunks, answer_eval)
    raw_text = generate_judge_text(JUDGE_SYSTEM_INSTRUCTIONS, prompt)
    result = normalize_judge(extract_json_object(raw_text))
    result["raw_text"] = raw_text
    return result


def judge_passed(judge_eval: dict | None) -> bool:
    if not judge_eval:
        return True
    scores = [judge_eval[key]["score"] for key in JUDGE_KEYS]
    return min(scores) >= 4 and not judge_eval.get("unsupported_claims")


def run_rag_command(command_template: str, question: str) -> dict:
    command = command_template.format(question=question)
    completed = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"RAG command failed: {command}")
    return json.loads(completed.stdout)


def records_by_id(records: list[dict]) -> dict[str, dict]:
    return {record["id"]: record for record in records if "id" in record}


def evaluate_item(item: dict, rag_result: dict, args: argparse.Namespace) -> dict:
    chunks = rag_result.get("retrieved_chunks", [])
    answer = rag_result.get("answer", "")
    retrieval_eval = evaluate_retrieval(item, chunks, args.page_window)
    answer_eval = evaluate_answer(item, answer) if answer else None
    graph_eval = evaluate_graph_context(item, rag_result)

    judge_eval = None
    llm_error = ""
    if args.judge and answer:
        try:
            judge_eval = judge_result(item, answer, chunks, answer_eval or {})
        except (RuntimeError, ValueError, json.JSONDecodeError) as error:
            llm_error = str(error)

    answer_passed = True if answer_eval is None else answer_eval["answer_checks_passed"]
    graph_passed = True if graph_eval is None else graph_eval["graph_checks_passed"]
    passed = (
        retrieval_eval["expected_sources_found"]
        and answer_passed
        and graph_passed
        and judge_passed(judge_eval)
        and not llm_error
    )

    return {
        "id": item["id"],
        "question": item["question"],
        "passed": passed,
        "retrieval_passed": retrieval_eval["expected_sources_found"],
        "answer_passed": answer_passed,
        "graph_passed": graph_passed,
        "judge_passed": judge_passed(judge_eval),
        "retrieval": retrieval_eval,
        "answer_eval": answer_eval,
        "graph_eval": graph_eval,
        "judge_eval": judge_eval,
        "llm_error": llm_error,
        "answer": answer if args.include_answers else "",
    }


def run_evaluation(args: argparse.Namespace) -> dict:
    questions = load_json_or_jsonl(args.questions)
    if args.limit:
        questions = questions[: args.limit]

    run_records = records_by_id(load_json_or_jsonl(args.runs)) if args.runs else {}
    results = []
    for item in questions:
        if args.rag_command:
            rag_result = run_rag_command(args.rag_command, item["question"])
        else:
            rag_result = run_records.get(item["id"], {})
        results.append(evaluate_item(item, rag_result, args))

    passed = sum(1 for result in results if result["passed"])
    return {
        "metadata": {
            "run_at": datetime.now().isoformat(timespec="seconds"),
            "questions": str(args.questions),
            "runs": str(args.runs) if args.runs else "",
            "judge": args.judge,
        },
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "pass_rate": round(passed / len(results), 3) if results else 0.0,
        },
        "results": results,
    }


def print_report(report: dict) -> None:
    summary = report["summary"]
    print(f"RAG evaluation passed {summary['passed']}/{summary['total']} ({summary['pass_rate']:.0%})")
    for result in report["results"]:
        status = "PASS" if result["passed"] else "FAIL"
        print(f"\n[{status}] {result['id']}")
        print(f"Question: {result['question']}")
        print(f"Retrieval passed: {result['retrieval_passed']}")
        if result.get("answer_eval"):
            print(f"Answer passed: {result['answer_passed']}")
            missing = result["answer_eval"]["missing_required_terms"]
            forbidden = result["answer_eval"]["present_forbidden_terms"]
            if missing:
                print("Missing terms: " + ", ".join(missing))
            if forbidden:
                print("Forbidden terms found: " + ", ".join(forbidden))
        if result.get("graph_eval"):
            graph_eval = result["graph_eval"]
            print(f"GraphRAG passed: {result['graph_passed']}")
            if graph_eval["missing_graph_nodes"]:
                print("Missing graph nodes: " + ", ".join(graph_eval["missing_graph_nodes"]))
            if graph_eval["missing_relations"]:
                print("Missing relations: " + ", ".join(graph_eval["missing_relations"]))
            if graph_eval["missing_literature_sources"]:
                print("Missing literature sources: " + ", ".join(graph_eval["missing_literature_sources"]))
        if result.get("judge_eval"):
            scores = " | ".join(f"{key}={result['judge_eval'][key]['score']}" for key in JUDGE_KEYS)
            print(f"Judge passed: {result['judge_passed']} | {scores}")
        if result.get("llm_error"):
            print(f"LLM error: {result['llm_error']}")


def save_report(report: dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Portable RAG evaluation engine.")
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS_PATH)
    parser.add_argument("--runs", type=Path, help="JSON/JSONL file with precomputed RAG outputs.")
    parser.add_argument(
        "--rag-command",
        help="Command template that returns one JSON result. Use {question} as placeholder.",
    )
    parser.add_argument("--page-window", type=int, default=0)
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--include-answers", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    engine_dir = Path(__file__).resolve().parent
    load_dotenv(engine_dir.parent / ".env")
    load_dotenv(engine_dir / ".env", override=True)
    args = parse_args()
    if not args.runs and not args.rag_command:
        raise SystemExit("Provide --runs or --rag-command.")
    report = run_evaluation(args)
    print_report(report)
    if args.save:
        print(f"\nSaved report: {save_report(report, args.output_dir)}")


if __name__ == "__main__":
    main()
