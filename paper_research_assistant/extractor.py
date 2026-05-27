from __future__ import annotations

from pathlib import Path
from typing import Any

from .text_utils import first_sentences, normalize_text, split_sections
from .utils import write_json


class TextExtractionError(RuntimeError):
    pass


def extract_pdf_text(path: Path) -> tuple[str, dict[str, Any]]:
    try:
        import fitz  # type: ignore
    except Exception:
        fitz = None

    if fitz is not None:
        try:
            doc = fitz.open(path)
            pages = [page.get_text("text") for page in doc]
            metadata = dict(doc.metadata or {})
            metadata["pageCount"] = len(doc)
            return "\n\n".join(pages), metadata
        except Exception as exc:
            raise TextExtractionError(f"PyMuPDF failed for {path.name}: {exc}") from exc

    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:
        raise TextExtractionError(
            "PDF extraction requires optional dependency: pip install pymupdf "
            "or pip install pypdf"
        ) from exc

    try:
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
        metadata = {str(k).strip("/"): str(v) for k, v in (reader.metadata or {}).items()}
        metadata["pageCount"] = len(reader.pages)
        return "\n\n".join(pages), metadata
    except Exception as exc:
        raise TextExtractionError(f"pypdf failed for {path.name}: {exc}") from exc


def extract_plain_text(path: Path) -> tuple[str, dict[str, Any]]:
    return path.read_text(encoding="utf-8", errors="replace"), {}


def refine_title(paper: dict[str, Any], sections: dict[str, str], metadata: dict[str, Any]) -> str:
    title = str(metadata.get("title") or metadata.get("Title") or "").strip()
    if title and len(title) > 5 and not title.lower().startswith("untitled"):
        return title

    full_text = sections.get("Full Text") or sections.get("Abstract") or ""
    for line in full_text.splitlines()[:15]:
        candidate = line.strip().lstrip("#").strip()
        if 8 <= len(candidate) <= 180 and not candidate.lower().startswith(("abstract", "arxiv")):
            return candidate
    return str(paper.get("title") or paper["fileName"])


def extract_paper_text(paper: dict[str, Any], text_dir: Path, force: bool = False) -> dict[str, Any]:
    output_path = text_dir / f"{paper['id'].replace(':', '__')}.json"
    if output_path.exists() and not force:
        try:
            cached = output_path.read_text(encoding="utf-8")
            import json

            parsed = json.loads(cached)
            if parsed.get("sha256") == paper.get("sha256"):
                return parsed
        except Exception:
            pass

    path = Path(paper["path"])
    try:
        if path.suffix.lower() == ".pdf":
            raw_text, metadata = extract_pdf_text(path)
        elif path.suffix.lower() in {".txt", ".md"}:
            raw_text, metadata = extract_plain_text(path)
        else:
            raise TextExtractionError(f"Unsupported file type: {path.suffix}")

        text = normalize_text(raw_text)
        sections = split_sections(text)
        extracted = {
            "paperId": paper["id"],
            "sha256": paper["sha256"],
            "title": refine_title(paper, sections, metadata),
            "sourcePath": paper["path"],
            "relativePath": paper["relativePath"],
            "metadata": metadata,
            "sections": sections,
            "abstract": first_sentences(sections.get("Abstract", ""), 4),
            "textLength": len(text),
            "status": "ok",
            "error": None,
        }
    except Exception as exc:
        extracted = {
            "paperId": paper["id"],
            "sha256": paper["sha256"],
            "title": paper.get("title") or paper["fileName"],
            "sourcePath": paper["path"],
            "relativePath": paper["relativePath"],
            "metadata": {},
            "sections": {},
            "abstract": "",
            "textLength": 0,
            "status": "failed",
            "error": str(exc),
        }

    write_json(output_path, extracted)
    return extracted


def extract_all_text(
    papers: list[dict[str, Any]],
    text_dir: Path,
    force: bool = False,
) -> list[dict[str, Any]]:
    return [extract_paper_text(paper, text_dir, force=force) for paper in papers]
