from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
NEW_RAG_DIR = Path(__file__).resolve().parent

RAW_PDF_DIR = ROOT_DIR / "data" / "raw_pdfs"
SOURCE_METADATA_JSON = ROOT_DIR / "data" / "source_metadata.json"

PROCESSED_DIR = NEW_RAG_DIR / "data" / "processed"
PAGES_JSONL = PROCESSED_DIR / "corpus_pages.jsonl"
DEFAULT_CHUNKS_PATH = PROCESSED_DIR / "corpus_chunks.jsonl"

VECTOR_DB_DIR = NEW_RAG_DIR / "data" / "vector_db" / "chroma"
COLLECTION_NAME = "new_rag_literature"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150
DEFAULT_TOP_K = 8
DEFAULT_VECTOR_K = 20
DEFAULT_BM25_K = 20
