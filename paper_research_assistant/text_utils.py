from __future__ import annotations

import re


SECTION_ALIASES: dict[str, str] = {
    "abstract": "Abstract",
    "summary": "Abstract",
    "introduction": "Introduction",
    "background": "Introduction",
    "related work": "Related Work",
    "literature review": "Related Work",
    "method": "Method",
    "methods": "Method",
    "methodology": "Method",
    "approach": "Method",
    "model": "Method",
    "proposed method": "Method",
    "experiments": "Experiments",
    "experiment": "Experiments",
    "experimental setup": "Experiments",
    "evaluation": "Experiments",
    "results": "Results",
    "discussion": "Discussion",
    "analysis": "Discussion",
    "limitations": "Limitations",
    "limitation": "Limitations",
    "future work": "Future Work",
    "conclusion": "Conclusion",
    "conclusions": "Conclusion",
    "references": "References",
    "bibliography": "References",
}


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"(?<![.!?:;])\n(?=[a-z0-9(])", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_heading(line: str) -> str:
    heading = line.strip()
    heading = re.sub(r"^#{1,6}\s+", "", heading)
    heading = re.sub(r"^\d+(\.\d+)*\s+", "", heading)
    heading = re.sub(r"^[IVXLC]+\.\s+", "", heading, flags=re.I)
    heading = re.sub(r"[:.\-–—]+$", "", heading).strip()
    heading = re.sub(r"\s+", " ", heading).lower()
    return heading


def split_sections(text: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {"Full Text": []}
    current = "Full Text"

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            sections.setdefault(current, []).append("")
            continue

        normalized = normalize_heading(line)
        canonical = SECTION_ALIASES.get(normalized)
        is_short_heading = len(line) <= 80 and canonical is not None
        if is_short_heading:
            current = canonical
            sections.setdefault(current, [])
            continue
        sections.setdefault(current, []).append(raw_line)

    compact: dict[str, str] = {}
    for name, lines in sections.items():
        content = normalize_text("\n".join(lines))
        if content:
            compact[name] = content
    return compact or {"Full Text": text}


def split_sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text)
    return [p.strip() for p in parts if len(p.strip()) > 20]


def first_sentences(text: str, count: int = 2) -> str:
    return " ".join(split_sentences(text)[:count]).strip()
