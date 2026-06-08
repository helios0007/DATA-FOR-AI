"""
chunk_papers.py — Reads PDFs from data/rag_documents/papers/, splits each into
~400-word chunks with 50-word overlap, tags each chunk with source/strategy/page,
and writes JSON arrays to data/rag_documents/chunks/<filename>.json.

Run from project root:
    python scripts/chunk_papers.py
"""

import json
import re
from pathlib import Path

from pypdf import PdfReader

PAPERS_DIR = Path("data/rag_documents/papers")
CHUNKS_DIR = Path("data/rag_documents/chunks")
CHUNK_WORDS = 400
OVERLAP_WORDS = 50

# Map filename stem keywords → strategy tag
FILENAME_TO_STRATEGY = {
    "balaras_1996":      "thermal_mass",
    "blocken_2007":      "cross_ventilation",
    "santamouris_2014":  "green_roof",
    "santamouris_1996":  "general",
    "lapisa_2018":       "shading",
    "evola_2017":        "night_purge",
    "szokolay_2004":     "general",
    "givoni_1994":       "general",
    "getter_rowe_2006":  "green_roof",
    "miguel_2016":       "general",
    "synergiceffects":   "general",
    "the_application_of_traditional_architect": "general",
}


def infer_strategy(stem: str) -> str:
    for key, strategy in FILENAME_TO_STRATEGY.items():
        if key in stem.lower():
            return strategy
    return "general"


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """Returns [(page_number, cleaned_text), ...]."""
    reader = PdfReader(str(pdf_path))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = re.sub(r"\s+", " ", raw).strip()
        if text:
            pages.append((i, text))
    return pages


def make_chunks(pages: list[tuple[int, str]]) -> list[dict]:
    """
    Flatten all words across pages, slide a window of CHUNK_WORDS with
    OVERLAP_WORDS step-back, record the page where each chunk starts.
    """
    # Build flat word list with page provenance
    all_words: list[tuple[str, int]] = []
    for page_num, text in pages:
        for word in text.split():
            all_words.append((word, page_num))

    chunks = []
    i = 0
    while i < len(all_words):
        window = all_words[i : i + CHUNK_WORDS]
        if not window:
            break
        text = " ".join(w for w, _ in window)
        page = window[0][1]
        chunks.append({"text": text, "page": page})
        i += CHUNK_WORDS - OVERLAP_WORDS

    return chunks


def process_pdf(pdf_path: Path) -> list[dict]:
    stem = pdf_path.stem
    strategy = infer_strategy(stem)
    # Human-readable source label
    source = stem.replace("_", " ").title()

    pages = extract_pages(pdf_path)
    raw_chunks = make_chunks(pages)

    return [
        {
            "id": f"{stem}_chunk_{idx:03d}",
            "source": source,
            "strategy": strategy,
            "page": str(chunk["page"]),
            "text": chunk["text"],
        }
        for idx, chunk in enumerate(raw_chunks, start=1)
    ]


def main():
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(PAPERS_DIR.glob("*.pdf"))

    if not pdfs:
        print(f"No PDFs found in {PAPERS_DIR}")
        return

    total_chunks = 0
    for pdf_path in pdfs:
        print(f"Processing {pdf_path.name} ...", end=" ")
        chunks = process_pdf(pdf_path)
        out_path = CHUNKS_DIR / f"{pdf_path.stem}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, indent=2, ensure_ascii=False)
        print(f"{len(chunks)} chunks -> {out_path.name}")
        total_chunks += len(chunks)

    print(f"\nDone. {len(pdfs)} files, {total_chunks} total chunks.")


if __name__ == "__main__":
    main()
