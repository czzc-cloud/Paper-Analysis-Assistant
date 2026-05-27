from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .utils import sha256_file, slugify

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}
OUTPUT_DIR_NAME = ".paper-research-assistant"


def infer_year(text: str) -> int | None:
    match = re.search(r"\b(19|20)\d{2}\b", text)
    return int(match.group(0)) if match else None


def infer_arxiv_id(text: str) -> str | None:
    match = re.search(r"\b(?:arxiv[:\s]*)?(\d{4}\.\d{4,5})(?:v\d+)?\b", text, re.I)
    return match.group(1) if match else None


def infer_doi(text: str) -> str | None:
    match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", text, re.I)
    return match.group(0) if match else None


def title_from_stem(path: Path) -> str:
    title = re.sub(r"[_-]+", " ", path.stem).strip()
    title = re.sub(r"\s+", " ", title)
    return title or path.stem


def scan_papers(input_dir: Path, limit: int | None = None) -> list[dict[str, Any]]:
    input_dir = input_dir.resolve()
    if not input_dir.exists() or not input_dir.is_dir():
        raise FileNotFoundError(f"Paper directory does not exist: {input_dir}")

    files: list[Path] = []
    for path in input_dir.rglob("*"):
        if not path.is_file():
            continue
        if OUTPUT_DIR_NAME in path.parts:
            continue
        if path.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(path)

    files.sort(key=lambda p: str(p.relative_to(input_dir)).lower())
    if limit is not None:
        files = files[:limit]

    used_ids: set[str] = set()
    papers: list[dict[str, Any]] = []
    for path in files:
        file_hash = sha256_file(path)
        rel_path = path.relative_to(input_dir).as_posix()
        base_id = f"paper:{slugify(path.stem, 'paper')}"
        paper_id = base_id
        if paper_id in used_ids:
            paper_id = f"{base_id}-{file_hash[:8]}"
        used_ids.add(paper_id)

        search_text = f"{path.name} {path.stem}"
        papers.append(
            {
                "id": paper_id,
                "path": str(path),
                "relativePath": rel_path,
                "fileName": path.name,
                "extension": path.suffix.lower(),
                "sha256": file_hash,
                "sizeBytes": path.stat().st_size,
                "title": title_from_stem(path),
                "year": infer_year(search_text),
                "doi": infer_doi(search_text),
                "arxivId": infer_arxiv_id(search_text),
                "status": "scanned",
            }
        )
    return papers
