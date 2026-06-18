from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader


def extract_pdf_pages(source: dict) -> list[dict]:
    pdf_path = source["pdf_path"]
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        pages.append(
            {
                "page": index,
                "source": pdf_path.name,
                "source_id": source["source_id"],
                "source_title": source["source_title"],
                "authors": source.get("authors", ""),
                "year": source.get("year", ""),
                "document_type": source.get("document_type", ""),
                "citation": source.get("citation", ""),
                "doi_or_url": source.get("doi_or_url", ""),
                "text": " ".join(text.split()),
            }
        )
    return pages


def write_jsonl(records: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for record in records:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as file:
        return [json.loads(line) for line in file if line.strip()]
