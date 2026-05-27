from __future__ import annotations

from pathlib import Path
from typing import Any

from .analyzer import analyze_all
from .extractor import extract_all_text
from .graph import build_graph
from .report import generate_report
from .scanner import OUTPUT_DIR_NAME, scan_papers
from .utils import ensure_dir, utc_now_iso, write_json, write_text


def analyze_directory(
    paper_dir: Path,
    output_dir: Path | None = None,
    force: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    paper_dir = paper_dir.resolve()
    if output_dir is None:
        output_dir = paper_dir / OUTPUT_DIR_NAME
    else:
        output_dir = output_dir.resolve()

    ensure_dir(output_dir)
    text_dir = ensure_dir(output_dir / "paper-text")

    papers = scan_papers(paper_dir, limit=limit)
    extracted = extract_all_text(papers, text_dir, force=force)

    extracted_by_id = {item["paperId"]: item for item in extracted}
    for paper in papers:
        extracted_item = extracted_by_id.get(paper["id"])
        if extracted_item:
            paper["title"] = extracted_item.get("title") or paper["title"]
            paper["status"] = extracted_item.get("status", "unknown")
            paper["error"] = extracted_item.get("error")

    analysis = analyze_all(extracted)
    graph = build_graph(papers, analysis)
    report = generate_report(papers, analysis, graph)

    papers_path = output_dir / "papers.json"
    analysis_path = output_dir / "analysis.json"
    graph_path = output_dir / "literature-graph.json"
    report_path = output_dir / "research-map-report.md"
    summary_path = output_dir / "run-summary.json"

    write_json(papers_path, {"generatedAt": utc_now_iso(), "papers": papers})
    write_json(analysis_path, analysis)
    write_json(graph_path, graph)
    write_text(report_path, report)

    summary = {
        "generatedAt": utc_now_iso(),
        "paperDir": str(paper_dir),
        "outputDir": str(output_dir),
        "papersScanned": len(papers),
        "successfulExtractions": sum(1 for item in extracted if item.get("status") == "ok"),
        "failedExtractions": sum(1 for item in extracted if item.get("status") != "ok"),
        "graphNodes": graph["stats"]["nodeCount"],
        "graphEdges": graph["stats"]["edgeCount"],
        "outputs": {
            "papers": str(papers_path),
            "analysis": str(analysis_path),
            "graph": str(graph_path),
            "report": str(report_path),
            "summary": str(summary_path),
        },
    }
    write_json(summary_path, summary)
    return summary
