"""
build_rag.py — Builds a ChromaDB vector store from chunked literature.
Reads JSON chunk files from data/rag_documents/chunks/ (produced by chunk_papers.py),
embeds them with sentence-transformers, and persists to graph/chroma_db/.

Run from project root:
    python scripts/chunk_papers.py   # first
    python scripts/build_rag.py
"""

import json
import os
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

CHUNKS_PATH  = Path("data/rag_documents/chunks")
CHROMA_PATH  = "graph/chroma_db"
COLLECTION   = "passive_design_knowledge"
EMBED_MODEL  = "all-MiniLM-L6-v2"
BATCH_SIZE   = 64


def build_rag():
    Path(CHROMA_PATH).mkdir(parents=True, exist_ok=True)

    print(f"Loading embedding model: {EMBED_MODEL} ...")
    model = SentenceTransformer(EMBED_MODEL)

    client = chromadb.PersistentClient(path=CHROMA_PATH)
    # Drop existing collection to allow clean rebuilds
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass
    collection = client.create_collection(COLLECTION)

    chunk_files = sorted(CHUNKS_PATH.glob("*.json"))
    if not chunk_files:
        print(f"No chunk files found in {CHUNKS_PATH}. Run chunk_papers.py first.")
        return

    total = 0
    for chunk_file in chunk_files:
        with open(chunk_file, encoding="utf-8") as f:
            chunks = json.load(f)

        if not chunks:
            continue

        print(f"Embedding {chunk_file.name} ({len(chunks)} chunks) ...", end=" ")

        # Process in batches
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = chunks[i : i + BATCH_SIZE]
            texts      = [c["text"]     for c in batch]
            ids        = [c["id"]       for c in batch]
            metadatas  = [
                {
                    "source":   c.get("source", ""),
                    "strategy": c.get("strategy", "general"),
                    "page":     str(c.get("page", "")),
                }
                for c in batch
            ]
            embeddings = model.encode(texts, show_progress_bar=False).tolist()
            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )

        print(f"done.")
        total += len(chunks)

    print(f"\nRAG store built: {total} chunks indexed in {CHROMA_PATH}")


if __name__ == "__main__":
    build_rag()
