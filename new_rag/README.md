# New RAG Architecture For The GitHub Project

This folder describes a proposed next-generation RAG system for the passive-design advisor GitHub project.

The goal is to improve retrieval accuracy, grounding, and recommendation quality while keeping the system realistic to implement.

## Proposed Pipeline

```text
PDF / literature corpus
-> semantic/contextual chunking
-> metadata extraction and strategy tagging
-> vector index
-> BM25 keyword index
-> graph index

User / strategy query
-> query classification
-> query rewriting / multi-query generation
-> metadata filtering
-> hybrid retrieval: BM25 + vector
-> GraphRAG relationship retrieval
-> candidate merge
-> reranking
-> evidence sufficiency check
-> final context assembly
-> LLM answer/recommendation
-> evaluation
```

## Runnable Prototype In This Folder

This folder now includes a small implementation that follows the GitHub project's GraphRAG direction:

- `source_catalog.py`: finds PDF literature sources and attaches metadata.
- `document_loader.py`: extracts pages from PDFs.
- `chunker.py`: creates overlapping text chunks.
- `ingest_literature.py`: runs source discovery, PDF extraction, and chunking.
- `index_builder.py`: builds the local Chroma vector index.
- `strategy_graph.py`: strategy graph with `has_variant`, `justified_by`, and `synergy_with` relationships.
- `retrieval.py`: hybrid retrieval using local BM25 plus the existing Chroma vector database.
- `retriever.py`: small retriever-facing import surface.
- `reranker.py`: small reranker-facing import surface.
- `rag.py`: main CLI for ingesting, indexing, testing, and asking.
- `sample_questions.json`: small test set grounded in the local literature chunks.
- `eval_questions.json`: eval-engine-compatible questions for `eva_engine`.
- `.env.example`: optional provider placeholders for future answer generation.

Generated chunks and vector indexes are stored under `new_rag/data/` and ignored by Git.

It does not replace the current RAG yet. It is a ready-to-test prototype for the improved retriever.

## Run It

```powershell
python new_rag\rag.py all
```

To export outputs for the evaluation engine:

```powershell
python new_rag\rag.py export-eval
python eva_engine\evaluate_rag.py --questions new_rag\eval_questions.json --runs new_rag\data\eval_runs\rag_outputs.json
```

## Realistic Assessment

The proposed system is strong, but implementing all parts at once would be risky.

The best practical approach is staged:

```text
Stage 1: contextual/semantic chunking + metadata
Stage 2: hybrid retrieval with BM25 + vector
Stage 3: reranking
Stage 4: GraphRAG integration
Stage 5: query rewriting / multi-query
Stage 6: sufficiency checks + evaluation loop
```

Do not start with a fully agentic RAG. The current GitHub project already has useful structure:

```text
strategy scoring
NetworkX graph
Chroma vector store
strategy metadata filters
```

The best upgrade is to improve evidence retrieval and context quality around that existing design.

## Recommended High-Accuracy Version

The strongest near-term architecture is:

```text
Contextual semantic chunks
+ hybrid BM25/vector retrieval
+ strategy metadata filters
+ graph expansion
+ reranker
+ sufficiency check
```

This is more realistic and useful than a very broad agentic system.

## Why This Approach

Technical design documents contain:

- exact terms
- strategy names
- standards
- citations
- page-specific evidence
- design options
- relations between strategies

Vector retrieval alone can miss exact terms. BM25 helps with exact words and identifiers. GraphRAG helps with relationships such as:

- `has_variant`
- `justified_by`
- `synergy_with`
- `no_conflict`

Reranking helps remove weak or noisy chunks before the LLM sees them.

## Source Ideas

This architecture follows current best practice patterns:

- hybrid BM25 + vector retrieval
- contextual chunks
- reranking after broad retrieval
- graph relationship retrieval for structured knowledge
- evaluation with deterministic checks and LLM-as-judge

See:

- `TERMINAL_INSTRUCTIONS.md`
- `rag.py`
