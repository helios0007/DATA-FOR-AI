# Terminal Instructions

Run from project root:

```powershell
cd C:\Users\Morris\OneDrive\Desktop\RAG
```

## Smoke Test

If the literature has already been ingested and indexed, run:

```powershell
python new_rag\rag.py ask "Why is external insulation preferred from a building physics perspective?"
```

## Full Pipeline From PDFs

Run these after adding or changing PDFs in `data\raw_pdfs`:

```powershell
python new_rag\rag.py ingest
python new_rag\rag.py index
python new_rag\rag.py test
```

Or run all three together:

```powershell
python new_rag\rag.py all
```

## Run The Literature Test Set

```powershell
python new_rag\rag.py test
```

## Export Test Set Results As JSON

```powershell
python new_rag\rag.py test --json
```

## Show Retrieved Text

```powershell
python new_rag\rag.py ask "Why are vapour barriers important when insulating roofs?" --show-text
```

## Export Eva Engine Compatible JSON

```powershell
python new_rag\rag.py export-eval
```

## Evaluate With Eva Engine

```powershell
python eva_engine\evaluate_rag.py --questions new_rag\eval_questions.json --runs new_rag\data\eval_runs\rag_outputs.json
```

## Use A Different Chunk File

```powershell
python new_rag\rag.py ask "What are HVAC service module considerations?" --chunks data\processed\corpus_chunks.jsonl
```

## Validate Python Syntax

```powershell
python -m py_compile new_rag\config.py new_rag\document_loader.py new_rag\source_catalog.py new_rag\chunker.py new_rag\ingest_literature.py new_rag\index_builder.py new_rag\strategy_graph.py new_rag\retrieval.py new_rag\retriever.py new_rag\reranker.py new_rag\rag.py
```
