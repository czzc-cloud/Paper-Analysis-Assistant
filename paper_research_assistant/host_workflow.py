from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .analyzer import infer_gaps, propose_methodologies
from .extractor import extract_all_text
from .graph import build_graph
from .report import generate_report
from .scanner import OUTPUT_DIR_NAME, scan_papers
from .utils import ensure_dir, read_json, utc_now_iso, write_json, write_text


def default_output_dir(paper_dir: Path) -> Path:
    return paper_dir.resolve() / OUTPUT_DIR_NAME


def prepare_host_analysis(
    paper_dir: Path,
    output_dir: Path | None = None,
    force: bool = False,
    limit: int | None = None,
    batch_size: int = 4,
) -> dict[str, Any]:
    paper_dir = paper_dir.resolve()
    output_dir = output_dir.resolve() if output_dir else default_output_dir(paper_dir)
    text_dir = ensure_dir(output_dir / "paper-text")
    intermediate_dir = ensure_dir(output_dir / "intermediate")

    papers = scan_papers(paper_dir, limit=limit)
    extracted = extract_all_text(papers, text_dir, force=force)

    extracted_by_id = {item["paperId"]: item for item in extracted}
    for paper in papers:
        extracted_item = extracted_by_id.get(paper["id"])
        if extracted_item:
            paper["title"] = extracted_item.get("title") or paper["title"]
            paper["status"] = extracted_item.get("status", "unknown")
            paper["error"] = extracted_item.get("error")
            paper["textPath"] = str(text_dir / f"{paper['id'].replace(':', '__')}.json")

    existing_index = load_existing_analysis_index(output_dir)
    for paper in papers:
        cached_hash = existing_index.get(paper["id"])
        if paper.get("status") == "ok" and cached_hash == paper.get("sha256"):
            paper["analysisStatus"] = "cached"
        elif paper.get("status") == "ok":
            paper["analysisStatus"] = "pending"
        else:
            paper["analysisStatus"] = "skipped"

    start_index = next_batch_index(intermediate_dir)
    batches = build_batches(papers, batch_size=batch_size, start_index=start_index)

    papers_path = output_dir / "papers.json"
    batches_path = intermediate_dir / "analysis-batches.json"
    summary_path = output_dir / "run-summary.json"

    write_json(papers_path, {"generatedAt": utc_now_iso(), "papers": papers})
    write_json(
        batches_path,
        {
            "generatedAt": utc_now_iso(),
            "batchSize": batch_size,
            "batches": batches,
            "cachedPaperIds": [
                paper["id"] for paper in papers if paper.get("analysisStatus") == "cached"
            ],
            "pendingPaperIds": [
                paper["id"] for paper in papers if paper.get("analysisStatus") == "pending"
            ],
            "instructions": (
                "Host model must read only papers listed in batches[].papers and write "
                "paper-analysis-<batchIndex>.json. cachedPaperIds already have matching "
                "analysis for the current sha256 and should not be re-read."
            ),
        },
    )

    summary = {
        "generatedAt": utc_now_iso(),
        "mode": "host-prepare",
        "paperDir": str(paper_dir),
        "outputDir": str(output_dir),
        "papersScanned": len(papers),
        "successfulExtractions": sum(1 for item in extracted if item.get("status") == "ok"),
        "failedExtractions": sum(1 for item in extracted if item.get("status") != "ok"),
        "cachedAnalyses": sum(1 for paper in papers if paper.get("analysisStatus") == "cached"),
        "pendingAnalyses": sum(1 for paper in papers if paper.get("analysisStatus") == "pending"),
        "batches": len(batches),
        "outputs": {
            "papers": str(papers_path),
            "paperTextDir": str(text_dir),
            "intermediateDir": str(intermediate_dir),
            "batches": str(batches_path),
            "summary": str(summary_path),
        },
    }
    write_json(summary_path, summary)
    return summary


def build_batches(
    papers: list[dict[str, Any]],
    batch_size: int,
    start_index: int = 1,
) -> list[dict[str, Any]]:
    ok_papers = [
        paper
        for paper in papers
        if paper.get("status") == "ok" and paper.get("analysisStatus") == "pending"
    ]
    batches: list[dict[str, Any]] = []
    for index in range(0, len(ok_papers), max(1, batch_size)):
        batch_index = start_index + len(batches)
        chunk = ok_papers[index : index + batch_size]
        batches.append(
            {
                "batchIndex": batch_index,
                "outputPath": f"paper-analysis-{batch_index}.json",
                "papers": [
                    {
                        "paperId": paper["id"],
                        "title": paper.get("title"),
                        "relativePath": paper.get("relativePath"),
                        "textPath": paper.get("textPath"),
                        "sourceHash": paper.get("sha256"),
                    }
                    for paper in chunk
                ],
            }
        )
    return batches


def finalize_host_analysis(
    paper_dir: Path,
    output_dir: Path | None = None,
    allow_partial: bool = False,
) -> dict[str, Any]:
    paper_dir = paper_dir.resolve()
    output_dir = output_dir.resolve() if output_dir else default_output_dir(paper_dir)
    intermediate_dir = output_dir / "intermediate"
    papers_manifest_path = output_dir / "papers.json"

    papers_manifest_data = read_json(papers_manifest_path)
    if not papers_manifest_data or "papers" not in papers_manifest_data:
        raise FileNotFoundError(f"Missing papers manifest: {papers_manifest_path}")
    papers_manifest = papers_manifest_data["papers"]

    paper_analyses = filter_current_analyses(
        load_paper_analyses(intermediate_dir),
        papers_manifest,
    )
    if not paper_analyses and not allow_partial:
        raise FileNotFoundError(
            f"No host model analysis files found in {intermediate_dir}. "
            "Expected paper-analysis-*.json."
        )

    analysis = build_corpus_analysis(paper_analyses, intermediate_dir)
    graph = build_graph(papers_manifest, analysis)
    report = generate_report(papers_manifest, analysis, graph)

    analysis_path = output_dir / "analysis.json"
    graph_path = output_dir / "literature-graph.json"
    report_path = output_dir / "research-map-report.md"
    summary_path = output_dir / "run-summary.json"

    write_json(analysis_path, analysis)
    write_json(graph_path, graph)
    write_text(report_path, report)

    summary = {
        "generatedAt": utc_now_iso(),
        "mode": "host-finalize",
        "paperDir": str(paper_dir),
        "outputDir": str(output_dir),
        "papersScanned": len(papers_manifest),
        "paperAnalyses": len(paper_analyses),
        "graphNodes": graph["stats"]["nodeCount"],
        "graphEdges": graph["stats"]["edgeCount"],
        "outputs": {
            "papers": str(papers_manifest_path),
            "analysis": str(analysis_path),
            "graph": str(graph_path),
            "report": str(report_path),
            "summary": str(summary_path),
        },
    }
    write_json(summary_path, summary)
    return summary


def next_batch_index(intermediate_dir: Path) -> int:
    max_index = 0
    if intermediate_dir.exists():
        for path in intermediate_dir.glob("paper-analysis-*.json"):
            stem = path.stem.removeprefix("paper-analysis-")
            if stem.isdigit():
                max_index = max(max_index, int(stem))
    return max_index + 1


def load_existing_analysis_index(output_dir: Path) -> dict[str, str]:
    intermediate_dir = output_dir / "intermediate"
    index: dict[str, str] = {}
    for analysis in load_paper_analyses(intermediate_dir):
        paper_id = analysis.get("paperId")
        source_hash = analysis.get("sourceHash")
        if paper_id and source_hash:
            index[str(paper_id)] = str(source_hash)

    merged = read_json(output_dir / "analysis.json", default={}) or {}
    if isinstance(merged.get("papers"), list):
        for analysis in merged["papers"]:
            paper_id = analysis.get("paperId")
            source_hash = analysis.get("sourceHash")
            if paper_id and source_hash:
                index[str(paper_id)] = str(source_hash)
    return index


def filter_current_analyses(
    analyses: list[dict[str, Any]],
    papers_manifest: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    current_hashes = {paper["id"]: paper.get("sha256") for paper in papers_manifest}
    grouped: dict[str, dict[str, Any]] = {}
    for analysis in analyses:
        paper_id = analysis.get("paperId")
        if paper_id not in current_hashes:
            continue
        source_hash = analysis.get("sourceHash")
        current_hash = current_hashes[paper_id]
        if source_hash and current_hash and source_hash != current_hash:
            continue

        existing = grouped.get(paper_id)
        if existing is None:
            grouped[paper_id] = analysis
            continue
        if not existing.get("sourceHash") and source_hash:
            grouped[paper_id] = analysis
            continue
        grouped[paper_id] = analysis
    return list(grouped.values())


def load_paper_analyses(intermediate_dir: Path) -> list[dict[str, Any]]:
    analyses: list[dict[str, Any]] = []
    if not intermediate_dir.exists():
        return analyses

    for path in sorted(intermediate_dir.glob("paper-analysis-*.json")):
        data = read_json(path)
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict) and isinstance(data.get("papers"), list):
            items = data["papers"]
        elif isinstance(data, dict) and data.get("paperId"):
            items = [data]
        else:
            raise ValueError(f"Invalid paper analysis shape: {path}")

        for item in items:
            analyses.append(normalize_paper_analysis(item, source_path=path))
    return analyses


def normalize_paper_analysis(item: dict[str, Any], source_path: Path) -> dict[str, Any]:
    if not item.get("paperId"):
        raise ValueError(f"Paper analysis missing paperId in {source_path}")

    def as_list(value: Any) -> list[Any]:
        return value if isinstance(value, list) else []

    return {
        "paperId": str(item["paperId"]),
        "title": str(item.get("title") or item["paperId"]),
        "status": str(item.get("status") or "ok"),
        "error": item.get("error"),
        "problem": str(item.get("problem") or ""),
        "coreIdea": str(item.get("coreIdea") or ""),
        "keyInnovations": normalize_innovations(as_list(item.get("keyInnovations")), item["paperId"]),
        "methods": normalize_named_items(as_list(item.get("methods"))),
        "datasets": normalize_named_items(as_list(item.get("datasets"))),
        "metrics": normalize_named_items(as_list(item.get("metrics"))),
        "limitations": normalize_text_items(as_list(item.get("limitations"))),
        "futureWork": normalize_text_items(as_list(item.get("futureWork"))),
        "directions": [str(v) for v in as_list(item.get("directions")) if str(v).strip()],
        "confidence": str(item.get("confidence") or "host-model"),
        "sourceHash": item.get("sourceHash"),
        "sourceAnalysisFile": str(source_path),
    }


def normalize_innovations(items: list[Any], paper_id: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    stem = str(paper_id).split(":", 1)[-1]
    for index, item in enumerate(items, start=1):
        if isinstance(item, str):
            text = item
            evidence = "unknown"
            innovation_type = "method"
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("claim") or "")
            evidence = str(item.get("evidence") or "unknown")
            innovation_type = str(item.get("innovationType") or "method")
        else:
            continue
        if not text.strip():
            continue
        normalized.append(
            {
                "id": f"claim:{stem}:host-{index}",
                "text": text.strip(),
                "evidence": evidence,
                "innovationType": innovation_type,
            }
        )
    return normalized


def normalize_named_items(items: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            name = item
            evidence = "unknown"
        elif isinstance(item, dict):
            name = str(item.get("name") or item.get("text") or "")
            evidence = str(item.get("evidence") or "unknown")
        else:
            continue
        if name.strip():
            normalized.append({"name": name.strip(), "evidence": evidence})
    return normalized


def normalize_text_items(items: list[Any]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in items:
        if isinstance(item, str):
            text = item
            evidence = "unknown"
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("claim") or "")
            evidence = str(item.get("evidence") or "unknown")
        else:
            continue
        if text.strip():
            normalized.append({"text": text.strip(), "evidence": evidence})
    return normalized


def build_corpus_analysis(
    paper_analyses: list[dict[str, Any]],
    intermediate_dir: Path,
) -> dict[str, Any]:
    direction_counts = Counter(
        direction for paper in paper_analyses for direction in paper.get("directions", [])
    )
    method_counts = Counter(
        method["name"] for paper in paper_analyses for method in paper.get("methods", [])
    )
    cooccurrence: dict[str, Counter[str]] = defaultdict(Counter)
    for paper in paper_analyses:
        for direction in paper.get("directions", []):
            for method in paper.get("methods", []):
                cooccurrence[direction][method["name"]] += 1

    deterministic_trends = [
        {
            "direction": direction,
            "paperCount": count,
            "topMethods": [name for name, _ in cooccurrence[direction].most_common(5)],
            "maturity": "mainstream" if count >= 3 else "emerging" if count == 2 else "underexplored",
        }
        for direction, count in direction_counts.most_common()
    ]

    corpus_file = intermediate_dir / "corpus-analysis.json"
    corpus = read_json(corpus_file, default={}) or {}

    trends = corpus.get("trends") if isinstance(corpus.get("trends"), list) else deterministic_trends
    gaps = corpus.get("gaps") if isinstance(corpus.get("gaps"), list) else infer_gaps(
        paper_analyses,
        direction_counts,
        method_counts,
    )
    suggestions = (
        corpus.get("methodologySuggestions")
        if isinstance(corpus.get("methodologySuggestions"), list)
        else propose_methodologies(trends, gaps, method_counts)
    )

    return {
        "papers": paper_analyses,
        "trends": trends,
        "gaps": gaps,
        "methodologySuggestions": suggestions,
        "stats": {
            "paperCount": len(paper_analyses),
            "successfulAnalyses": sum(1 for paper in paper_analyses if paper.get("status") == "ok"),
            "failedAnalyses": sum(1 for paper in paper_analyses if paper.get("status") != "ok"),
            "directionCounts": dict(direction_counts),
            "methodCounts": dict(method_counts),
            "analysisMode": "host-model",
        },
    }
