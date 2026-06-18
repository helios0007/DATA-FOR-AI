from __future__ import annotations

import json
import re
from pathlib import Path

from config import RAW_PDF_DIR, SOURCE_METADATA_JSON


def make_source_id(pdf_path: Path) -> str:
    source_id = re.sub(r"[^a-zA-Z0-9]+", "_", pdf_path.stem).strip("_")
    return source_id.upper() or "SOURCE"


def make_source_title(pdf_path: Path) -> str:
    title = re.sub(r"[_-]+", " ", pdf_path.stem)
    title = re.sub(r"\s+", " ", title).strip()
    return title.title() or pdf_path.name


def load_source_metadata() -> dict[str, dict]:
    if not SOURCE_METADATA_JSON.exists():
        return {}

    with SOURCE_METADATA_JSON.open("r", encoding="utf-8") as file:
        metadata = json.load(file)

    if not isinstance(metadata, dict):
        raise ValueError(f"{SOURCE_METADATA_JSON} must contain a JSON object keyed by PDF filename.")
    return metadata


def build_source_record(pdf_path: Path, metadata: dict) -> dict:
    title = metadata.get("source_title") or metadata.get("title") or make_source_title(pdf_path)
    source_id = metadata.get("source_id") or make_source_id(pdf_path)
    return {
        "pdf_path": pdf_path,
        "source": pdf_path.name,
        "source_id": source_id,
        "source_title": title,
        "authors": metadata.get("authors", ""),
        "year": metadata.get("year", ""),
        "document_type": metadata.get("document_type") or metadata.get("type", ""),
        "citation": metadata.get("citation", ""),
        "doi_or_url": metadata.get("doi_or_url") or metadata.get("url", ""),
    }


def discover_sources(raw_pdf_dir: Path = RAW_PDF_DIR) -> list[dict]:
    metadata_by_filename = load_source_metadata()
    pdf_paths = sorted(raw_pdf_dir.glob("*.pdf"))
    return [
        build_source_record(pdf_path, metadata_by_filename.get(pdf_path.name, {}))
        for pdf_path in pdf_paths
    ]
