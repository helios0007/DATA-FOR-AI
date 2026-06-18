# Terminal Instructions

Run commands from the project root unless noted otherwise.

## 1. Test With Included Sample Files

```powershell
python eva_engine\evaluate_rag.py --runs eva_engine\sample_rag_outputs.json
```

Expected result:

```text
RAG evaluation passed 1/1 (100%)
```

## 2. Evaluate Your Own RAG Outputs

```powershell
python eva_engine\evaluate_rag.py --questions path\to\eval_questions.json --runs path\to\rag_outputs.json
```

Example:

```powershell
python eva_engine\evaluate_rag.py --questions tests\rag_eval_questions.json --runs data\my_rag_outputs.json
```

## 3. Allow Nearby Page Matches

Use this if PDF page extraction has an offset:

```powershell
python eva_engine\evaluate_rag.py --runs data\my_rag_outputs.json --page-window 1
```

This treats expected page `13` as matching pages `12`, `13`, or `14`.

## 4. Save A Report

```powershell
python eva_engine\evaluate_rag.py --runs data\my_rag_outputs.json --save
```

Reports are saved to:

```text
eva_engine/runs/
```

## 5. Include Answers In Saved Reports

```powershell
python eva_engine\evaluate_rag.py --runs data\my_rag_outputs.json --include-answers --save
```

## 6. Run Only First N Questions

Useful while testing:

```powershell
python eva_engine\evaluate_rag.py --runs data\my_rag_outputs.json --limit 3
```

## 7. Use LLM Judge Mode

First edit:

```text
eva_engine/.env
```

If `.env` does not exist, copy:

```powershell
Copy-Item eva_engine\.env.example eva_engine\.env
```

For OpenAI:

```env
JUDGE_PROVIDER=openai
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4.1-mini
```

Then run:

```powershell
python eva_engine\evaluate_rag.py --runs data\my_rag_outputs.json --judge --limit 1
```

For Gemini:

```env
JUDGE_PROVIDER=gemini
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-2.0-flash
```

For Claude:

```env
JUDGE_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-5-haiku-latest
```

For Ollama:

```env
JUDGE_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
OLLAMA_URL=http://localhost:11434/api/generate
```

Judge mode costs extra because it calls an LLM once per evaluated answer.

## 8. Evaluate By Calling Another RAG Project Directly

If another project can answer one question and print JSON to stdout, use:

```powershell
python eva_engine\evaluate_rag.py --questions tests\rag_eval_questions.json --rag-command "python other_rag.py --json ""{question}"""
```

The command must return JSON like:

```json
{
  "answer": "Generated answer...",
  "retrieved_chunks": [
    {
      "text": "Chunk text...",
      "metadata": {
        "source_title": "Source title",
        "page": 13
      }
    }
  ]
}
```

For reliability, precomputed `--runs` files are recommended over `--rag-command`.

## 9. GraphRAG Evaluation

If your RAG output contains `graph_context`, run the same command:

```powershell
python eva_engine\evaluate_rag.py --questions path\to\graph_eval_questions.json --runs path\to\graph_rag_outputs.json
```

The evaluator will automatically run graph checks if the question file includes fields such as:

```text
expected_strategy
expected_graph_nodes
expected_relations
expected_literature_sources
```

## 10. Validate The Evaluator Script

```powershell
python -m py_compile eva_engine\evaluate_rag.py
```
