# Portable RAG Evaluation Engine

This folder contains a portable evaluation engine that can be copied into another RAG project.

It does not require the original `app/config.py`, `rag_retriever.py`, or `llm_answerer.py`.

## What It Evaluates

The engine checks:

- expected source/page retrieval
- required answer terms
- forbidden unsupported terms
- citation format
- optional LLM-as-judge scores

Judge mode scores:

- context relevance
- context sufficiency
- answer relevance
- faithfulness
- citation quality
- overall quality

## Folder Contents

```text
eva_engine/
|-- evaluate_rag.py
|-- sample_eval_questions.json
|-- sample_rag_outputs.json
|-- .env
|-- .env.example
|-- TERMINAL_INSTRUCTIONS.md
`-- README.md
```

## Expected Question Format

Create a JSON file like:

```json
[
  {
    "id": "q1",
    "question": "What does the guide say about external insulation?",
    "expected_sources": [
      {
        "source_title": "Building Envelope Retrofit Solution Booklet",
        "pages": [13]
      }
    ],
    "required_answer_terms": ["continuous insulation", "thermal bridges"],
    "forbidden_answer_terms": ["internal insulation is always preferred"]
  }
]
```

## Expected RAG Output Format

The evaluator needs each RAG result to contain:

```json
[
  {
    "id": "q1",
    "answer": "Generated answer with citations...",
    "retrieved_chunks": [
      {
        "text": "Retrieved chunk text...",
        "metadata": {
          "source_title": "Source title",
          "source_id": "SOURCE_ID",
          "page": 13
        },
        "score": 0.91
      }
    ]
  }
]
```

You can generate this file from any RAG system.

## Optional GraphRAG Format

For GraphRAG systems, such as the passive-design advisor repository, the evaluator can also check graph-specific expectations.

Add graph expectations to the question file:

```json
{
  "id": "shading_question",
  "question": "What shading strategy is recommended?",
  "expected_strategy": "shading",
  "expected_graph_nodes": ["shading", "shading_fixed_louvers", "szokolay_2004"],
  "expected_relations": ["has_variant", "justified_by"],
  "expected_literature_sources": ["szokolay_2004"],
  "expected_sources": [
    {
      "source_title": "Passive Design Literature",
      "pages": [12]
    }
  ],
  "required_answer_terms": ["shading", "solar gain"],
  "forbidden_answer_terms": ["active mechanical cooling"]
}
```

Then include `graph_context` in the RAG output:

```json
{
  "id": "shading_question",
  "answer": "Generated recommendation...",
  "retrieved_chunks": [],
  "graph_context": {
    "strategy": "shading",
    "nodes": [
      {
        "id": "shading",
        "type": "strategy",
        "label": "shading"
      },
      {
        "id": "shading_fixed_louvers",
        "type": "design_option",
        "label": "Fixed horizontal louvers"
      },
      {
        "id": "szokolay_2004",
        "type": "paper",
        "label": "Szokolay 2004"
      }
    ],
    "edges": [
      {
        "source": "shading",
        "target": "shading_fixed_louvers",
        "relation": "has_variant"
      },
      {
        "source": "shading",
        "target": "szokolay_2004",
        "relation": "justified_by"
      }
    ],
    "literature_sources": ["szokolay_2004"]
  }
}
```

GraphRAG checks are optional. If no graph expectations are present, the evaluator behaves like a normal RAG evaluator.

## Terminal Instructions

See:

```text
eva_engine/TERMINAL_INSTRUCTIONS.md
```

Quick smoke test:

```powershell
python eva_engine\evaluate_rag.py --runs eva_engine\sample_rag_outputs.json
```

## Copilot Integration Prompt

Use this prompt with GitHub Copilot Chat, ChatGPT, or another coding assistant when adding this evaluation engine to an existing RAG project:

```text
You are helping me integrate a portable RAG evaluation engine into this project.

Goal:
Connect eva_engine/evaluate_rag.py to the existing RAG pipeline without rewriting the RAG system.

The evaluator expects either:

1. A precomputed JSON/JSONL file passed with --runs
2. A command passed with --rag-command that returns one JSON object per question

Required output schema for each RAG result:

{
  "id": "question_id",
  "answer": "Generated answer text with citations",
  "retrieved_chunks": [
    {
      "text": "Retrieved chunk text",
      "metadata": {
        "source_title": "Source title",
        "source_id": "Optional source id",
        "page": 13
      },
      "score": 0.91
    }
  ]
}

Please inspect the existing RAG code and create the smallest adapter needed.

Preferred implementation:
- Add a small script such as scripts/export_rag_eval_outputs.py
- Read eva_engine/sample_eval_questions.json or my project-specific eval questions
- For each question, call the existing retriever and answer generator
- Save results as JSON to data/eval_runs/rag_outputs.json
- If the project uses GraphRAG, include graph_context with strategy, nodes, edges, and literature_sources
- Do not change the production RAG behavior
- Do not commit API keys or .env files

After the adapter is created, the evaluator should run with:

python eva_engine/evaluate_rag.py --questions path/to/eval_questions.json --runs data/eval_runs/rag_outputs.json

If judge mode is needed, use:

python eva_engine/evaluate_rag.py --questions path/to/eval_questions.json --runs data/eval_runs/rag_outputs.json --judge --limit 1

Keep changes minimal, document the command, and verify with one sample question first.
```

## Copilot Checklist

When using Copilot to integrate this evaluator, ask it to verify:

- The adapter returns `answer` and `retrieved_chunks`.
- Each chunk includes `text`.
- Each chunk includes `metadata.source_title`.
- Each chunk includes `metadata.page`.
- The question IDs in the RAG output match the IDs in the eval questions file.
- For GraphRAG, `graph_context.strategy` is present when expected.
- For GraphRAG, `graph_context.nodes[]` includes graph node IDs or labels.
- For GraphRAG, `graph_context.edges[]` includes relation names such as `has_variant` and `justified_by`.
- For GraphRAG, literature/standard nodes are included as nodes or `literature_sources`.
- `.env` files and API keys are not committed.
- Large generated outputs are ignored or saved outside version control.
- The first test uses `--limit 1`.

## What To Copy Into Another Project

Minimum:

```text
eva_engine/evaluate_rag.py
eva_engine/README.md
eva_engine/.env.example
```

Also create project-specific:

```text
eval_questions.json
rag_outputs.json
```

## Git Safety

Do not commit real API keys.

If this folder is committed, replace secrets in:

```text
eva_engine/.env
```

with blank placeholders.

Recommended commit behavior:

```text
commit eva_engine/.env.example
do not commit eva_engine/.env
```
