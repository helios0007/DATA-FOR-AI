from __future__ import annotations

import argparse
import sys
from pathlib import Path

from chunker import chunk_pages
from config import CHUNK_OVERLAP, CHUNK_SIZE, PAGES_JSONL, RAW_PDF_DIR, DEFAULT_CHUNKS_PATH
from document_loader import extract_pdf_pages, write_jsonl
from source_catalog import discover_sources


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract PDF pages and create new_rag chunks.")
    parser.add_argument("--raw-pdf-dir", type=Path, default=RAW_PDF_DIR)
    parser.add_argument("--pages-out", type=Path, default=PAGES_JSONL)
    parser.add_argument("--chunks-out", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--chunk-size", type=int, default=CHUNK_SIZE)
    parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP)
    return parser.parse_args()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    args = parse_args()
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


if __name__ == "__main__":
    main()
