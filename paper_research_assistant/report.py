from __future__ import annotations

from collections import Counter
from typing import Any


def bullet_items(items: list[str], empty: str = "None detected") -> str:
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def generate_report(
    papers_manifest: list[dict[str, Any]],
    analysis: dict[str, Any],
    graph: dict[str, Any],
) -> str:
    papers = analysis.get("papers", [])
    successful = [paper for paper in papers if paper.get("status") == "ok"]
    failed = [paper for paper in papers if paper.get("status") != "ok"]
    analysis_mode = analysis.get("stats", {}).get("analysisMode", "heuristic")
    if analysis_mode == "host-model":
        mode_note = (
            "> Note: Semantic analysis was provided by the host model through "
            "`paper-analysis-*.json`; Python only merged and rendered the artifacts."
        )
    else:
        mode_note = (
            "> Note: This run used heuristic extraction. Treat research gaps and "
            "method suggestions as planning signals, not final literature-review claims."
        )

    lines: list[str] = [
        "# Research Map Report",
        "",
        "## Corpus Overview",
        "",
        f"- Papers scanned: {len(papers_manifest)}",
        f"- Successfully analyzed: {len(successful)}",
        f"- Failed: {len(failed)}",
        f"- Graph nodes: {graph.get('stats', {}).get('nodeCount', 0)}",
        f"- Graph edges: {graph.get('stats', {}).get('edgeCount', 0)}",
        "",
        mode_note,
        "",
    ]

    lines.extend(render_paper_summaries(successful))
    lines.extend(render_trends(analysis.get("trends", [])))
    lines.extend(render_gaps(analysis.get("gaps", [])))
    lines.extend(render_methodology_suggestions(analysis.get("methodologySuggestions", [])))

    if failed:
        lines.extend(["", "## Failed Papers", ""])
        for paper in failed:
            lines.append(f"- `{paper.get('paperId')}`: {paper.get('error')}")

    return "\n".join(lines).rstrip() + "\n"


def render_paper_summaries(papers: list[dict[str, Any]]) -> list[str]:
    lines = ["## Paper Summaries", ""]
    if not papers:
        lines.extend(["No papers were successfully analyzed.", ""])
        return lines

    for paper in papers:
        lines.extend(
            [
                f"### {paper.get('title') or paper['paperId']}",
                "",
                f"- ID: `{paper['paperId']}`",
                f"- Confidence: {paper.get('confidence', 'unknown')}",
                f"- Directions: {', '.join(paper.get('directions', [])) or 'None detected'}",
                f"- Problem: {paper.get('problem') or 'Not extracted'}",
                f"- Core idea: {paper.get('coreIdea') or 'Not extracted'}",
                "",
                "**Key innovations**",
            ]
        )
        innovations = [
            f"{item['text']} _(evidence: {item.get('evidence', 'unknown')}; type: {item.get('innovationType', 'method')})_"
            for item in paper.get("keyInnovations", [])[:5]
        ]
        lines.append(bullet_items(innovations, "No innovation sentence detected"))
        lines.extend(["", "**Methods**"])
        lines.append(bullet_items([item["name"] for item in paper.get("methods", [])], "No method keyword detected"))
        lines.extend(["", "**Limitations / future work**"])
        lines.append(bullet_items([item["text"] for item in paper.get("limitations", [])[:4]], "No limitation sentence detected"))
        lines.append("")
    return lines


def render_trends(trends: list[dict[str, Any]]) -> list[str]:
    lines = ["## Mainstream And Emerging Directions", ""]
    if not trends:
        lines.extend(["- No direction signal detected.", ""])
        return lines

    for trend in trends:
        methods = ", ".join(trend.get("topMethods", [])) or "No dominant method detected"
        lines.append(
            f"- **{trend['direction']}**: {trend['paperCount']} paper(s), maturity `{trend['maturity']}`, top methods: {methods}"
        )
    lines.append("")
    return lines


def render_gaps(gaps: list[dict[str, Any]]) -> list[str]:
    lines = ["## Research Gaps", ""]
    if not gaps:
        lines.extend(["- No gap signal detected. Add more papers or use LLM analysis for stronger gap discovery.", ""])
        return lines

    for gap in gaps:
        supporting = ", ".join(gap.get("supportingPapers", [])) or "not tied to a specific paper"
        lines.extend(
            [
                f"### {gap['name']}",
                "",
                f"- Type: {gap.get('type', 'unknown')}",
                f"- Why it may be underexplored: {gap.get('whyUnderexplored', '')}",
                f"- Supporting papers: {supporting}",
                f"- Risk: {gap.get('risk', 'unknown')}",
                f"- Potential value: {gap.get('potentialValue', '')}",
                "",
            ]
        )
    return lines


def render_methodology_suggestions(suggestions: list[dict[str, Any]]) -> list[str]:
    lines = ["## Method Innovation Suggestions", ""]
    if not suggestions:
        lines.extend(["- No methodology suggestion generated.", ""])
        return lines

    for suggestion in suggestions:
        methods = ", ".join(suggestion.get("candidateMethods", [])) or "No candidate method detected"
        lines.extend(
            [
                f"### {suggestion['title']}",
                "",
                f"- Basis: {suggestion.get('basis', 'unknown')}",
                f"- Idea: {suggestion.get('idea', '')}",
                f"- Candidate methods: {methods}",
                f"- Experiment sketch: {suggestion.get('experimentSketch', '')}",
                "",
            ]
        )
    return lines
