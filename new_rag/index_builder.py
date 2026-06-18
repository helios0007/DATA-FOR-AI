from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from config import COLLECTION_NAME, DEFAULT_CHUNKS_PATH, VECTOR_DB_DIR
from document_loader import read_jsonl


def get_collection(collection_name: str = COLLECTION_NAME):
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=DefaultEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection(collection_name: str = COLLECTION_NAME):
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        pass
    return get_collection(collection_name)


def index_chunks(chunks_path: Path = DEFAULT_CHUNKS_PATH, reset: bool = True) -> int:
    chunks = read_jsonl(chunks_path)
    collection = reset_collection() if reset else get_collection()
    collection.upsert(
        ids=[chunk["id"] for chunk in chunks],
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[chunk["metadata"] for chunk in chunks],
    )
    return len(chunks)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the new_rag Chroma vector index.")
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--no-reset", action="store_true")
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
    count = index_chunks(args.chunks, reset=not args.no_reset)
    print(f"Indexed {count} chunks into {VECTOR_DB_DIR} / {COLLECTION_NAME}")


if __name__ == "__main__":
    main()
