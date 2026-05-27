from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import Any

from .utils import slugify, utc_now_iso


TOP_METHODS_PER_DIRECTION = 6
MAX_METHOD_THEMES = 60
MAX_GAP_THEMES = 24
MAX_METHOD_SIMILARITY_EDGES = 120
MAX_PAPER_SIMILARITY_EDGES = 120


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "method",
    "methods",
    "model",
    "models",
    "network",
    "networks",
    "of",
    "on",
    "or",
    "paper",
    "the",
    "to",
    "via",
    "with",
}


LIMITATION_THEME_KEYWORDS = {
    "robustness": ["robust", "noisy", "noise", "shift", "generalization", "domain"],
    "scalability": ["scalability", "scale", "large", "cost", "expensive", "memory", "latency"],
    "data-quality": ["data", "annotation", "label", "quality", "imbalance", "scarce"],
    "evaluation": ["evaluation", "benchmark", "metric", "experiment", "validation"],
    "fine-grained-recognition": ["fine", "small", "local", "granular", "detail", "object"],
    "teacher-dependence": ["teacher", "distillation", "student", "pretrain"],
    "retrieval-quality": ["retrieval", "ranking", "evidence", "index"],
    "multimodal-alignment": ["modal", "alignment", "image", "text", "vision", "language"],
}


def node_id(kind: str, name: str) -> str:
    return f"{kind}:{slugify(name, kind)}"


def add_node(nodes: dict[str, dict[str, Any]], node: dict[str, Any]) -> None:
    existing = nodes.get(node["id"])
    if existing:
        existing.setdefault("metadata", {}).update(node.get("metadata", {}))
        existing["tags"] = sorted(set(existing.get("tags", []) + node.get("tags", [])))
        if node.get("summary") and not existing.get("summary"):
            existing["summary"] = node["summary"]
        return
    nodes[node["id"]] = node


def add_edge(edges: dict[tuple[str, str, str], dict[str, Any]], edge: dict[str, Any]) -> None:
    key = (edge["source"], edge["target"], edge["type"])
    existing = edges.get(key)
    if existing:
        existing["weight"] = max(float(existing.get("weight", 1.0)), float(edge.get("weight", 1.0)))
        existing.setdefault("metadata", {}).update(edge.get("metadata", {}))
        return
    edges[key] = edge


def text_tokens(value: str) -> set[str]:
    tokens = set()
    for raw_token in re.findall(r"[a-z0-9]+", value.lower()):
        token = normalize_token(raw_token)
        if len(token) < 3 or token in STOP_WORDS:
            continue
        tokens.add(token)
    return tokens


def normalize_token(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and len(token) > 4 and not token.endswith(("ss", "is", "us")):
        return token[:-1]
    return token


def overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def list_overlap_score(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def method_similarity(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    shared_tokens = sorted(left["tokens"] & right["tokens"])
    shared_directions = sorted(left["directions"] & right["directions"])
    shared_papers = sorted(left["papers"] & right["papers"])

    token_score = overlap_score(left["tokens"], right["tokens"])
    direction_score = list_overlap_score(left["directions"], right["directions"])
    paper_score = list_overlap_score(left["papers"], right["papers"])
    score = min(1.0, (token_score * 0.7) + (direction_score * 0.18) + (paper_score * 0.12))

    return score, {
        "sharedTokens": shared_tokens[:8],
        "sharedDirections": shared_directions[:6],
        "sharedPapers": shared_papers[:6],
    }


def paper_similarity(left: dict[str, Any], right: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    shared_directions = sorted(left["directions"] & right["directions"])
    shared_methods = sorted(left["methodThemeIds"] & right["methodThemeIds"])
    direction_score = list_overlap_score(left["directions"], right["directions"])
    method_score = list_overlap_score(left["methodThemeIds"], right["methodThemeIds"])
    score = min(1.0, direction_score * 0.56 + method_score * 0.44)
    return score, {
        "sharedDirections": shared_directions[:6],
        "sharedMethodThemes": shared_methods[:8],
    }


def build_graph(
    papers_manifest: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    manifest_by_id = {paper["id"]: paper for paper in papers_manifest}
    papers = [paper for paper in analysis.get("papers", []) if paper.get("status", "ok") == "ok"]
    trend_by_direction = build_trend_index(analysis)

    method_themes = build_method_themes(papers)
    gap_themes = build_gap_themes(papers, analysis, method_themes)

    direction_to_papers: dict[str, set[str]] = defaultdict(set)
    direction_to_method_themes: dict[str, Counter[str]] = defaultdict(Counter)
    direction_to_gap_themes: dict[str, set[str]] = defaultdict(set)
    paper_contexts: dict[str, dict[str, Any]] = {}

    for theme in method_themes.values():
        for paper_id in theme["papers"]:
            paper_contexts.setdefault(
                paper_id,
                {"directions": set(), "methodThemeIds": set(), "gapThemeIds": set()},
            )["methodThemeIds"].add(theme["id"])
        for direction in theme["directions"]:
            direction_to_method_themes[direction][theme["id"]] += len(theme["papers"])

    for theme in gap_themes.values():
        for paper_id in theme["papers"]:
            paper_contexts.setdefault(
                paper_id,
                {"directions": set(), "methodThemeIds": set(), "gapThemeIds": set()},
            )["gapThemeIds"].add(theme["id"])
        for direction in theme["directions"]:
            direction_to_gap_themes[direction].add(theme["id"])

    for paper in papers:
        paper_id = paper["paperId"]
        context = paper_contexts.setdefault(
            paper_id,
            {"directions": set(), "methodThemeIds": set(), "gapThemeIds": set()},
        )
        for direction in paper.get("directions", []) or ["general-research"]:
            context["directions"].add(direction)
            direction_to_papers[direction].add(paper_id)

    selected_method_ids = select_method_themes(method_themes, direction_to_method_themes)
    selected_gap_ids = select_gap_themes(gap_themes)

    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[tuple[str, str, str], dict[str, Any]] = {}

    add_paper_nodes(nodes, papers, manifest_by_id, paper_contexts)
    add_direction_nodes(
        nodes,
        direction_to_papers,
        direction_to_method_themes,
        direction_to_gap_themes,
        trend_by_direction,
    )
    add_method_nodes(nodes, method_themes, selected_method_ids, len(papers))
    add_gap_nodes(nodes, gap_themes, selected_gap_ids, len(papers))

    add_paper_direction_edges(edges, paper_contexts)
    add_direction_method_edges(edges, direction_to_method_themes, method_themes, selected_method_ids)
    add_direction_gap_edges(edges, direction_to_gap_themes, gap_themes, selected_gap_ids)
    add_method_similarity_edges(edges, method_themes, selected_method_ids)
    add_paper_similarity_edges(edges, paper_contexts, method_themes)

    graph = {
        "version": "2.0.0",
        "kind": "literature-overview",
        "generatedAt": utc_now_iso(),
        "nodes": sorted(nodes.values(), key=lambda item: (item["type"], item["id"])),
        "edges": sorted(edges.values(), key=lambda item: (item["source"], item["target"], item["type"])),
        "stats": {
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "paperCount": len([node for node in nodes.values() if node["type"] == "paper"]),
            "directionCount": len([node for node in nodes.values() if node["type"] == "direction"]),
            "methodThemeCount": len([node for node in nodes.values() if node["type"] == "method"]),
            "gapCount": len([node for node in nodes.values() if node["type"] == "gap"]),
            "view": "overview",
        },
        "metadata": {
            "description": (
                "Overview graph optimized for research directions, method themes, "
                "underexplored gaps, and cross-paper overlap. Datasets, metrics, and "
                "individual claims remain in analysis.json/report details rather than default graph nodes."
            )
        },
        "insights": build_insights(
            papers=papers,
            analysis=analysis,
            direction_to_papers=direction_to_papers,
            direction_to_method_themes=direction_to_method_themes,
            direction_to_gap_themes=direction_to_gap_themes,
            method_themes=method_themes,
            gap_themes=gap_themes,
            selected_method_ids=selected_method_ids,
            selected_gap_ids=selected_gap_ids,
            trend_by_direction=trend_by_direction,
            paper_contexts=paper_contexts,
        ),
    }
    return graph


def build_trend_index(analysis: dict[str, Any]) -> dict[str, dict[str, Any]]:
    trends: dict[str, dict[str, Any]] = {}
    for item in analysis.get("trends", []):
        if not isinstance(item, dict):
            continue
        direction = str(item.get("direction") or "").strip()
        if direction:
            trends[direction] = item
    return trends


def build_method_themes(papers: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    themes: dict[str, dict[str, Any]] = {}
    for paper in papers:
        paper_id = paper["paperId"]
        directions = set(paper.get("directions", []) or ["general-research"])
        for method in paper.get("methods", []):
            name = str(method.get("name") or "").strip()
            if not name:
                continue
            tokens = text_tokens(name)
            if not tokens:
                continue
            theme = find_matching_method_theme(themes, tokens)
            if theme is None:
                theme_id = node_id("method", canonical_method_name(name))
                theme = themes.setdefault(
                    theme_id,
                    {
                        "id": theme_id,
                        "names": Counter(),
                        "tokens": set(),
                        "papers": set(),
                        "directions": set(),
                        "evidence": {},
                    },
                )
            theme["names"][name] += 1
            theme["tokens"].update(tokens)
            theme["papers"].add(paper_id)
            theme["directions"].update(directions)
            if method.get("evidence"):
                theme["evidence"].setdefault(paper_id, method.get("evidence"))

    for theme in themes.values():
        theme["name"] = theme["names"].most_common(1)[0][0]
        theme["aliases"] = [name for name, _ in theme["names"].most_common(8)]
    return themes


def find_matching_method_theme(
    themes: dict[str, dict[str, Any]],
    tokens: set[str],
) -> dict[str, Any] | None:
    best_theme: dict[str, Any] | None = None
    best_score = 0.0
    for theme in themes.values():
        score = overlap_score(tokens, theme["tokens"])
        shared = tokens & theme["tokens"]
        if score > best_score and (score >= 0.58 or len(shared) >= 3):
            best_theme = theme
            best_score = score
    return best_theme


def canonical_method_name(name: str) -> str:
    tokens = sorted(text_tokens(name))
    return "-".join(tokens[:6]) or name


def build_gap_themes(
    papers: list[dict[str, Any]],
    analysis: dict[str, Any],
    method_themes: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    themes: dict[str, dict[str, Any]] = {}

    for gap in analysis.get("gaps", []):
        name = str(gap.get("name") or "").strip()
        if not name:
            continue
        paper_ids = set(str(paper_id) for paper_id in gap.get("supportingPapers", []) if paper_id)
        directions = infer_directions_for_papers(papers, paper_ids)
        theme_id = node_id("gap", name)
        themes[theme_id] = {
            "id": theme_id,
            "name": name,
            "summary": gap.get("whyUnderexplored") or gap.get("potentialValue") or name,
            "gapType": gap.get("type", "underexplored"),
            "papers": paper_ids,
            "directions": directions,
            "terms": text_tokens(name),
            "source": "corpus-gap",
            "risk": gap.get("risk"),
            "potentialValue": gap.get("potentialValue"),
            "rareMethods": gap.get("rareMethods", []),
            "commonMethods": gap.get("commonMethods", []),
        }

    for paper in papers:
        paper_id = paper["paperId"]
        directions = set(paper.get("directions", []) or ["general-research"])
        for item in paper.get("limitations", []) + paper.get("futureWork", []):
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            name = infer_limitation_theme_name(text)
            theme_id = node_id("gap", name)
            theme = themes.setdefault(
                theme_id,
                {
                    "id": theme_id,
                    "name": name,
                    "summary": text,
                    "gapType": "limitation-driven",
                    "papers": set(),
                    "directions": set(),
                    "terms": text_tokens(name),
                    "source": "paper-limitations",
                    "examples": [],
                },
            )
            theme["papers"].add(paper_id)
            theme["directions"].update(directions)
            theme.setdefault("examples", []).append({"paperId": paper_id, "text": text, "evidence": item.get("evidence")})

    rare_methods = [
        theme for theme in method_themes.values() if len(theme["papers"]) == 1 and len(theme["directions"]) >= 1
    ]
    for theme in sorted(rare_methods, key=lambda item: item["name"])[:MAX_GAP_THEMES]:
        gap_name = f"Underexplored method: {theme['name']}"
        theme_id = node_id("gap", gap_name)
        themes.setdefault(
            theme_id,
            {
                "id": theme_id,
                "name": gap_name,
                "summary": "This method appears in only one local paper, so it may represent an underexplored method path in the current corpus.",
                "gapType": "low-coverage-method",
                "papers": set(theme["papers"]),
                "directions": set(theme["directions"]),
                "terms": set(theme["tokens"]),
                "source": "method-coverage",
                "methodThemeId": theme["id"],
            },
        )

    return themes


def infer_directions_for_papers(papers: list[dict[str, Any]], paper_ids: set[str]) -> set[str]:
    directions: set[str] = set()
    for paper in papers:
        if paper["paperId"] in paper_ids:
            directions.update(paper.get("directions", []) or ["general-research"])
    return directions


def infer_limitation_theme_name(text: str) -> str:
    tokens = text_tokens(text)
    for theme, keywords in LIMITATION_THEME_KEYWORDS.items():
        if tokens & set(keywords):
            return theme
    if not tokens:
        return "underexplored-limitation"
    return " ".join(sorted(tokens)[:4])


def select_method_themes(
    method_themes: dict[str, dict[str, Any]],
    direction_to_method_themes: dict[str, Counter[str]],
) -> set[str]:
    selected: set[str] = set()
    for counter in direction_to_method_themes.values():
        selected.update(theme_id for theme_id, _ in counter.most_common(TOP_METHODS_PER_DIRECTION))

    ranked = sorted(
        method_themes.values(),
        key=lambda theme: (len(theme["papers"]), len(theme["directions"]), sum(theme["names"].values()), theme["name"]),
        reverse=True,
    )
    selected.update(theme["id"] for theme in ranked[:MAX_METHOD_THEMES])

    rare_ranked = sorted(
        [theme for theme in method_themes.values() if len(theme["papers"]) == 1],
        key=lambda theme: (len(theme["directions"]), sum(theme["names"].values()), theme["name"]),
        reverse=True,
    )
    selected.update(theme["id"] for theme in rare_ranked[: max(8, MAX_METHOD_THEMES // 5)])

    return {
        theme["id"]
        for theme in sorted(
            [theme for theme in method_themes.values() if theme["id"] in selected],
            key=lambda item: (
                len(item["papers"]),
                len(item["directions"]),
                sum(item["names"].values()),
                item["name"],
            ),
            reverse=True,
        )[:MAX_METHOD_THEMES]
    }


def select_gap_themes(gap_themes: dict[str, dict[str, Any]]) -> set[str]:
    ranked = sorted(
        gap_themes.values(),
        key=lambda theme: (len(theme["papers"]), len(theme["directions"]), theme["name"]),
        reverse=True,
    )
    return {theme["id"] for theme in ranked[:MAX_GAP_THEMES]}


def build_insights(
    papers: list[dict[str, Any]],
    analysis: dict[str, Any],
    direction_to_papers: dict[str, set[str]],
    direction_to_method_themes: dict[str, Counter[str]],
    direction_to_gap_themes: dict[str, set[str]],
    method_themes: dict[str, dict[str, Any]],
    gap_themes: dict[str, dict[str, Any]],
    selected_method_ids: set[str],
    selected_gap_ids: set[str],
    trend_by_direction: dict[str, dict[str, Any]],
    paper_contexts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    paper_total = max(1, len(papers))
    max_direction_count = max((len(paper_ids) for paper_ids in direction_to_papers.values()), default=1)

    methods_by_area = [
        build_area_insight(
            direction=direction,
            paper_ids=paper_ids,
            direction_to_method_themes=direction_to_method_themes,
            direction_to_gap_themes=direction_to_gap_themes,
            method_themes=method_themes,
            gap_themes=gap_themes,
            selected_method_ids=selected_method_ids,
            selected_gap_ids=selected_gap_ids,
            trend_by_direction=trend_by_direction,
            max_direction_count=max_direction_count,
        )
        for direction, paper_ids in direction_to_papers.items()
    ]
    methods_by_area.sort(
        key=lambda item: (item["paperCount"], item["methodCount"], item["gapCount"], item["name"]),
        reverse=True,
    )

    hot_methods = build_hot_method_insights(method_themes, selected_method_ids, paper_total)
    research_gaps = build_gap_insights(gap_themes, selected_gap_ids, paper_total)

    underexplored_areas = sorted(
        [
            {
                **area,
                "opportunityScore": round(
                    (1.0 - min(1.0, area["paperCount"] / max_direction_count)) * 0.52
                    + min(1.0, area["gapCount"] / 4) * 0.33
                    + min(1.0, area["methodCount"] / 6) * 0.15,
                    3,
                ),
            }
            for area in methods_by_area
            if area["maturity"] == "underexplored" or area["gapCount"] > 0
        ],
        key=lambda item: (item["opportunityScore"], item["gapCount"], item["name"]),
        reverse=True,
    )

    suggestions = normalize_methodology_suggestions(analysis.get("methodologySuggestions", []))

    return {
        "scope": "local-corpus",
        "summary": {
            "paperCount": len(papers),
            "researchAreaCount": len(direction_to_papers),
            "methodThemeCount": len(method_themes),
            "gapCount": len(gap_themes),
            "mainstreamAreaCount": sum(1 for item in methods_by_area if item["maturity"] == "mainstream"),
            "underexploredAreaCount": sum(1 for item in methods_by_area if item["maturity"] == "underexplored"),
            "analysisMode": analysis.get("stats", {}).get("analysisMode", "heuristic"),
        },
        "topResearchAreas": methods_by_area[:8],
        "hotMethods": hot_methods[:12],
        "methodsByArea": methods_by_area,
        "underexploredAreas": underexplored_areas[:10],
        "researchGaps": research_gaps[:12],
        "methodologySuggestions": suggestions[:12],
        "paperEvidenceCount": len(paper_contexts),
    }


def build_area_insight(
    direction: str,
    paper_ids: set[str],
    direction_to_method_themes: dict[str, Counter[str]],
    direction_to_gap_themes: dict[str, set[str]],
    method_themes: dict[str, dict[str, Any]],
    gap_themes: dict[str, dict[str, Any]],
    selected_method_ids: set[str],
    selected_gap_ids: set[str],
    trend_by_direction: dict[str, dict[str, Any]],
    max_direction_count: int,
) -> dict[str, Any]:
    trend = trend_by_direction.get(direction, {})
    maturity = normalized_maturity(trend.get("maturity")) or maturity_label(len(paper_ids), max_direction_count)
    heat = math.log1p(len(paper_ids)) / max(1.0, math.log1p(max_direction_count))

    methods = []
    for theme_id, _ in direction_to_method_themes.get(direction, Counter()).most_common(12):
        theme = method_themes.get(theme_id)
        if not theme or theme_id not in selected_method_ids:
            continue
        overlap = set(theme["papers"]) & paper_ids
        if not overlap:
            continue
        methods.append(
            {
                "id": theme_id,
                "name": theme["name"],
                "paperCount": len(overlap),
                "coverage": round(len(overlap) / max(1, len(paper_ids)), 3),
                "directions": sorted(theme["directions"]),
            }
        )

    gaps = []
    for gap_id in sorted(direction_to_gap_themes.get(direction, set())):
        theme = gap_themes.get(gap_id)
        if not theme or gap_id not in selected_gap_ids:
            continue
        gaps.append(
            {
                "id": gap_id,
                "name": theme["name"],
                "gapType": theme.get("gapType"),
                "paperCount": len(set(theme["papers"]) & paper_ids),
            }
        )

    trend_top_methods = as_string_list(trend.get("topMethods", []))

    return {
        "id": node_id("direction", direction),
        "name": direction,
        "paperCount": len(paper_ids),
        "paperIds": sorted(paper_ids),
        "heat": round(heat, 3),
        "maturity": maturity,
        "methodCount": len(methods),
        "gapCount": len(gaps),
        "topMethods": methods[:6],
        "trendTopMethods": trend_top_methods[:8],
        "gaps": gaps[:5],
    }


def build_hot_method_insights(
    method_themes: dict[str, dict[str, Any]],
    selected_method_ids: set[str],
    paper_total: int,
) -> list[dict[str, Any]]:
    max_direction_count = max(
        (len(theme["directions"]) for theme in method_themes.values() if theme["id"] in selected_method_ids),
        default=1,
    )
    max_mentions = max(
        (sum(theme["names"].values()) for theme in method_themes.values() if theme["id"] in selected_method_ids),
        default=1,
    )
    items = []
    for theme_id in selected_method_ids:
        theme = method_themes.get(theme_id)
        if not theme:
            continue
        paper_count = len(theme["papers"])
        direction_count = len(theme["directions"])
        mentions = sum(theme["names"].values())
        hotness = (
            (paper_count / max(1, paper_total)) * 0.58
            + (direction_count / max(1, max_direction_count)) * 0.3
            + (mentions / max(1, max_mentions)) * 0.12
        )
        items.append(
            {
                "id": theme_id,
                "name": theme["name"],
                "paperCount": paper_count,
                "coverage": round(paper_count / max(1, paper_total), 3),
                "directionCount": direction_count,
                "directions": sorted(theme["directions"]),
                "aliases": theme["aliases"][:6],
                "hotness": round(min(1.0, hotness), 3),
            }
        )
    return sorted(items, key=lambda item: (item["hotness"], item["paperCount"], item["name"]), reverse=True)


def build_gap_insights(
    gap_themes: dict[str, dict[str, Any]],
    selected_gap_ids: set[str],
    paper_total: int,
) -> list[dict[str, Any]]:
    items = []
    for gap_id in selected_gap_ids:
        theme = gap_themes.get(gap_id)
        if not theme:
            continue
        paper_count = len(theme["papers"])
        items.append(
            {
                "id": gap_id,
                "name": theme["name"],
                "summary": theme.get("summary"),
                "gapType": theme.get("gapType"),
                "paperCount": paper_count,
                "coverage": round(paper_count / max(1, paper_total), 3),
                "directions": sorted(theme["directions"]),
                "paperIds": sorted(theme["papers"]),
                "risk": theme.get("risk"),
                "potentialValue": theme.get("potentialValue"),
                "source": theme.get("source"),
            }
        )
    return sorted(items, key=lambda item: (item["paperCount"], item["name"]), reverse=True)


def normalize_methodology_suggestions(items: Any) -> list[dict[str, Any]]:
    normalized = []
    if not isinstance(items, list):
        return normalized
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or f"Method idea {index}").strip()
        normalized.append(
            {
                "title": title,
                "basis": str(item.get("basis") or "Inferred"),
                "idea": str(item.get("idea") or ""),
                "candidateMethods": as_string_list(item.get("candidateMethods", [])),
                "experimentSketch": str(item.get("experimentSketch") or ""),
            }
        )
    return normalized


def add_paper_nodes(
    nodes: dict[str, dict[str, Any]],
    papers: list[dict[str, Any]],
    manifest_by_id: dict[str, dict[str, Any]],
    paper_contexts: dict[str, dict[str, Any]],
) -> None:
    for paper in papers:
        paper_id = paper["paperId"]
        manifest = manifest_by_id.get(paper_id, {})
        context = paper_contexts.get(paper_id, {})
        add_node(
            nodes,
            {
                "id": paper_id,
                "type": "paper",
                "name": paper.get("title") or manifest.get("title") or paper_id,
                "summary": paper.get("coreIdea") or paper.get("problem") or "No summary extracted.",
                "tags": ["paper"] + sorted(context.get("directions", set())),
                "metadata": {
                    "path": manifest.get("path"),
                    "relativePath": manifest.get("relativePath"),
                    "year": manifest.get("year"),
                    "doi": manifest.get("doi"),
                    "arxivId": manifest.get("arxivId"),
                    "confidence": paper.get("confidence"),
                    "status": paper.get("status"),
                    "directionIds": [node_id("direction", value) for value in sorted(context.get("directions", set()))],
                    "methodThemeIds": sorted(context.get("methodThemeIds", set())),
                    "gapThemeIds": sorted(context.get("gapThemeIds", set())),
                    "paperIds": [paper_id],
                    "paperCount": 1,
                    "heat": 1.0,
                    "role": "evidence",
                },
            },
        )


def add_direction_nodes(
    nodes: dict[str, dict[str, Any]],
    direction_to_papers: dict[str, set[str]],
    direction_to_method_themes: dict[str, Counter[str]],
    direction_to_gap_themes: dict[str, set[str]],
    trend_by_direction: dict[str, dict[str, Any]],
) -> None:
    max_count = max((len(paper_ids) for paper_ids in direction_to_papers.values()), default=1)
    denominator = max(1.0, math.log1p(max_count))
    for direction, paper_ids in sorted(direction_to_papers.items()):
        direction_id = node_id("direction", direction)
        paper_count = len(paper_ids)
        heat = math.log1p(paper_count) / denominator
        trend = trend_by_direction.get(direction, {})
        maturity = normalized_maturity(trend.get("maturity")) or maturity_label(paper_count, max_count)
        trend_top_methods = as_string_list(trend.get("topMethods", []))
        add_node(
            nodes,
            {
                "id": direction_id,
                "type": "direction",
                "name": direction,
                "summary": f"{paper_count} local paper(s) are mapped to this research direction.",
                "tags": ["research-direction", maturity],
                "metadata": {
                    "paperIds": sorted(paper_ids),
                    "paperCount": paper_count,
                    "heat": round(heat, 3),
                    "maturity": maturity,
                    "methodThemeIds": [theme_id for theme_id, _ in direction_to_method_themes[direction].most_common(8)],
                    "gapThemeIds": sorted(direction_to_gap_themes.get(direction, set())),
                    "trendTopMethods": trend_top_methods[:8],
                    "trendPaperCount": trend.get("paperCount"),
                },
            },
        )


def normalized_maturity(value: Any) -> str | None:
    if value in {"mainstream", "emerging", "underexplored"}:
        return str(value)
    return None


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def maturity_label(count: int, max_count: int) -> str:
    if count >= max(3, math.ceil(max_count * 0.35)):
        return "mainstream"
    if count >= 2:
        return "emerging"
    return "underexplored"


def add_method_nodes(
    nodes: dict[str, dict[str, Any]],
    method_themes: dict[str, dict[str, Any]],
    selected_method_ids: set[str],
    paper_total: int,
) -> None:
    denominator = max(1.0, math.log1p(max(1, paper_total)))
    for theme_id in selected_method_ids:
        theme = method_themes.get(theme_id)
        if not theme:
            continue
        paper_count = len(theme["papers"])
        heat = math.log1p(paper_count) / denominator
        coverage = paper_count / max(1, paper_total)
        tags = ["method-theme"]
        tags.append("mainstream" if coverage >= 0.2 and paper_count >= 2 else "underexplored")
        add_node(
            nodes,
            {
                "id": theme_id,
                "type": "method",
                "name": theme["name"],
                "summary": f"Method theme appearing in {paper_count} local paper(s).",
                "tags": tags,
                "metadata": {
                    "aliases": theme["aliases"],
                    "paperIds": sorted(theme["papers"]),
                    "paperCount": paper_count,
                    "directionIds": [node_id("direction", direction) for direction in sorted(theme["directions"])],
                    "directions": sorted(theme["directions"]),
                    "coverage": round(coverage, 3),
                    "heat": round(heat, 3),
                    "evidence": theme["evidence"],
                    "tokens": sorted(theme["tokens"]),
                },
            },
        )


def add_gap_nodes(
    nodes: dict[str, dict[str, Any]],
    gap_themes: dict[str, dict[str, Any]],
    selected_gap_ids: set[str],
    paper_total: int,
) -> None:
    denominator = max(1.0, math.log1p(max(1, paper_total)))
    for theme_id in selected_gap_ids:
        theme = gap_themes.get(theme_id)
        if not theme:
            continue
        paper_count = len(theme["papers"])
        heat = math.log1p(max(1, paper_count)) / denominator
        coverage = paper_count / max(1, paper_total)
        tags = ["research-gap", theme.get("gapType", "underexplored")]
        if coverage <= 0.08 or paper_count <= 1:
            tags.append("underexplored")
        add_node(
            nodes,
            {
                "id": theme_id,
                "type": "gap",
                "name": theme["name"],
                "summary": theme.get("summary") or "Underexplored area inferred from the corpus.",
                "tags": tags,
                "metadata": {
                    "gapType": theme.get("gapType"),
                    "paperIds": sorted(theme["papers"]),
                    "paperCount": paper_count,
                    "directionIds": [node_id("direction", direction) for direction in sorted(theme["directions"])],
                    "directions": sorted(theme["directions"]),
                    "coverage": round(coverage, 3),
                    "heat": round(heat, 3),
                    "risk": theme.get("risk"),
                    "potentialValue": theme.get("potentialValue"),
                    "source": theme.get("source"),
                    "examples": theme.get("examples", [])[:4],
                    "rareMethods": theme.get("rareMethods", [])[:6],
                    "commonMethods": theme.get("commonMethods", [])[:6],
                    "methodThemeId": theme.get("methodThemeId"),
                },
            },
        )


def add_paper_direction_edges(
    edges: dict[tuple[str, str, str], dict[str, Any]],
    paper_contexts: dict[str, dict[str, Any]],
) -> None:
    for paper_id, context in paper_contexts.items():
        for direction in context.get("directions", set()):
            add_edge(
                edges,
                {
                    "source": paper_id,
                    "target": node_id("direction", direction),
                    "type": "belongs_to_direction",
                    "weight": 0.35,
                },
            )


def add_direction_method_edges(
    edges: dict[tuple[str, str, str], dict[str, Any]],
    direction_to_method_themes: dict[str, Counter[str]],
    method_themes: dict[str, dict[str, Any]],
    selected_method_ids: set[str],
) -> None:
    for direction, counter in direction_to_method_themes.items():
        max_count = max(counter.values(), default=1)
        for theme_id, count in counter.items():
            if theme_id not in selected_method_ids or theme_id not in method_themes:
                continue
            add_edge(
                edges,
                {
                    "source": node_id("direction", direction),
                    "target": theme_id,
                    "type": "uses_method_theme",
                    "weight": round(0.35 + 0.65 * (count / max_count), 3),
                    "metadata": {
                        "paperCount": len(method_themes[theme_id]["papers"]),
                        "direction": direction,
                    },
                },
            )


def add_direction_gap_edges(
    edges: dict[tuple[str, str, str], dict[str, Any]],
    direction_to_gap_themes: dict[str, set[str]],
    gap_themes: dict[str, dict[str, Any]],
    selected_gap_ids: set[str],
) -> None:
    for direction, gap_ids in direction_to_gap_themes.items():
        for gap_id in gap_ids:
            if gap_id not in selected_gap_ids or gap_id not in gap_themes:
                continue
            add_edge(
                edges,
                {
                    "source": node_id("direction", direction),
                    "target": gap_id,
                    "type": "has_research_gap",
                    "weight": 0.45 + min(0.45, len(gap_themes[gap_id]["papers"]) * 0.12),
                    "metadata": {"direction": direction},
                },
            )


def add_method_similarity_edges(
    edges: dict[tuple[str, str, str], dict[str, Any]],
    method_themes: dict[str, dict[str, Any]],
    selected_method_ids: set[str],
) -> None:
    candidates: list[tuple[float, str, str, dict[str, Any]]] = []
    selected = [method_themes[theme_id] for theme_id in selected_method_ids if theme_id in method_themes]
    for index, left in enumerate(selected):
        for right in selected[index + 1 :]:
            score, metadata = method_similarity(left, right)
            if score >= 0.2 and metadata["sharedTokens"]:
                candidates.append((score, left["id"], right["id"], metadata))

    degree: dict[str, int] = defaultdict(int)
    for score, source_id, target_id, metadata in sorted(candidates, reverse=True):
        if len([edge for edge in edges.values() if edge["type"] == "similar_method"]) >= MAX_METHOD_SIMILARITY_EDGES:
            break
        if degree[source_id] >= 5 or degree[target_id] >= 5:
            continue
        degree[source_id] += 1
        degree[target_id] += 1
        add_edge(
            edges,
            {
                "source": source_id,
                "target": target_id,
                "type": "similar_method",
                "weight": round(score, 3),
                "metadata": metadata,
            },
        )


def add_paper_similarity_edges(
    edges: dict[tuple[str, str, str], dict[str, Any]],
    paper_contexts: dict[str, dict[str, Any]],
    method_themes: dict[str, dict[str, Any]],
) -> None:
    paper_items = list(paper_contexts.items())
    candidates: list[tuple[float, str, str, dict[str, Any]]] = []
    for index, (left_id, left_context) in enumerate(paper_items):
        for right_id, right_context in paper_items[index + 1 :]:
            score, metadata = paper_similarity(left_context, right_context)
            if score >= 0.34 and (metadata["sharedDirections"] or metadata["sharedMethodThemes"]):
                metadata["sharedMethodThemeNames"] = [
                    method_themes[theme_id]["name"]
                    for theme_id in metadata["sharedMethodThemes"]
                    if theme_id in method_themes
                ][:6]
                candidates.append((score, left_id, right_id, metadata))

    degree: dict[str, int] = defaultdict(int)
    for score, source_id, target_id, metadata in sorted(candidates, reverse=True)[:MAX_PAPER_SIMILARITY_EDGES]:
        if degree[source_id] >= 3 or degree[target_id] >= 3:
            continue
        degree[source_id] += 1
        degree[target_id] += 1
        add_edge(
            edges,
            {
                "source": source_id,
                "target": target_id,
                "type": "paper_overlap",
                "weight": round(score, 3),
                "metadata": metadata,
            },
        )
