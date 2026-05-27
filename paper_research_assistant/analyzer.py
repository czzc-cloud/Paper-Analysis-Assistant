from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import Any

from .text_utils import first_sentences, split_sentences
from .utils import slugify

INNOVATION_KEYWORDS = [
    "novel",
    "new",
    "propose",
    "proposed",
    "introduce",
    "present",
    "contribution",
    "innovative",
    "first",
    "improve",
    "improves",
    "outperform",
    "framework",
    "method",
    "approach",
    "address",
    "解决",
    "提出",
    "创新",
    "首次",
    "改进",
    "方法",
    "框架",
]

LIMITATION_KEYWORDS = [
    "limitation",
    "limited",
    "challenge",
    "future work",
    "fail",
    "failure",
    "cannot",
    "does not",
    "requires",
    "expensive",
    "cost",
    "bias",
    "noise",
    "scalability",
    "局限",
    "不足",
    "挑战",
    "未来工作",
    "成本",
    "偏差",
]

DIRECTION_KEYWORDS: dict[str, list[str]] = {
    "retrieval-augmented-generation": ["retrieval", "rag", "rerank", "search", "knowledge base"],
    "large-language-models": ["large language model", "llm", "prompt", "instruction tuning", "chatgpt", "gpt"],
    "multimodal-learning": ["multimodal", "vision-language", "image-text", "cross-modal", "audio-visual"],
    "graph-learning": ["graph neural", "gnn", "knowledge graph", "graph convolution", "graph attention"],
    "representation-learning": ["representation learning", "embedding", "contrastive", "self-supervised"],
    "reinforcement-learning": ["reinforcement learning", "policy", "reward", "agent", "markov"],
    "causal-inference": ["causal", "counterfactual", "treatment effect", "confounder"],
    "optimization": ["optimization", "gradient", "regularization", "objective", "loss function"],
    "efficient-models": ["efficient", "compression", "distillation", "quantization", "pruning", "low-rank"],
    "robustness-and-safety": ["robust", "safety", "adversarial", "alignment", "hallucination", "fairness"],
    "time-series": ["time series", "forecasting", "temporal", "sequence modeling"],
    "medical-ai": ["clinical", "medical", "healthcare", "diagnosis", "patient"],
}

METHOD_KEYWORDS: dict[str, list[str]] = {
    "transformer": ["transformer", "attention mechanism", "self-attention", "cross-attention"],
    "contrastive learning": ["contrastive learning", "contrastive loss", "infoNCE"],
    "retrieval augmentation": ["retrieval augmented", "retrieval-augmented", "rag", "retriever"],
    "knowledge graph": ["knowledge graph", "entity graph", "relation graph"],
    "graph neural network": ["graph neural network", "gnn", "graph convolution", "graph attention"],
    "diffusion model": ["diffusion model", "denoising diffusion", "score-based"],
    "reinforcement learning": ["reinforcement learning", "policy gradient", "actor-critic", "q-learning"],
    "self-supervised learning": ["self-supervised", "masked modeling", "pretext task"],
    "prompt engineering": ["prompt engineering", "prompt tuning", "chain-of-thought", "cot"],
    "fine-tuning": ["fine-tuning", "finetuning", "instruction tuning", "adapter", "lora"],
    "distillation": ["distillation", "teacher-student", "student model"],
    "federated learning": ["federated learning"],
    "causal modeling": ["causal inference", "causal graph", "counterfactual"],
    "bayesian method": ["bayesian", "variational inference", "posterior"],
    "active learning": ["active learning", "uncertainty sampling"],
    "meta learning": ["meta-learning", "few-shot learning", "maml"],
}

COMMON_DATASETS = [
    "ImageNet",
    "COCO",
    "CIFAR-10",
    "CIFAR-100",
    "MNIST",
    "SQuAD",
    "GLUE",
    "SuperGLUE",
    "MMLU",
    "WikiText",
    "PubMed",
    "ArXiv",
    "Cora",
    "Citeseer",
    "OGB",
]

COMMON_METRICS = [
    "accuracy",
    "precision",
    "recall",
    "f1",
    "auc",
    "roc",
    "bleu",
    "rouge",
    "meteor",
    "map",
    "ndcg",
    "mae",
    "mse",
    "rmse",
    "perplexity",
    "latency",
    "throughput",
]


def text_for_analysis(extracted: dict[str, Any]) -> str:
    sections = extracted.get("sections") or {}
    preferred = [
        "Abstract",
        "Introduction",
        "Related Work",
        "Method",
        "Experiments",
        "Results",
        "Discussion",
        "Limitations",
        "Future Work",
        "Conclusion",
    ]
    parts = [str(sections[name]) for name in preferred if sections.get(name)]
    if not parts:
        parts = [str(v) for v in sections.values()]
    return "\n\n".join(parts)


def find_keyword_sentences(
    sections: dict[str, str],
    keywords: list[str],
    max_items: int = 6,
    skip_sections: set[str] | None = None,
) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    lowered_keywords = [k.lower() for k in keywords]
    skip_sections = skip_sections or set()
    for section_name, section_text in sections.items():
        if section_name == "References" or section_name in skip_sections:
            continue
        for sentence in split_sentences(section_text):
            lower = sentence.lower()
            if any(keyword in lower for keyword in lowered_keywords):
                found.append({"text": sentence, "evidence": section_name})
                if len(found) >= max_items:
                    return found
    return found


def detect_methods(text: str) -> list[dict[str, str]]:
    lower = text.lower()
    methods: list[dict[str, str]] = []
    for name, keywords in METHOD_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in lower:
                methods.append({"name": name, "evidence": keyword})
                break
    return methods


def detect_directions(text: str) -> list[str]:
    lower = text.lower()
    directions: list[str] = []
    for direction, keywords in DIRECTION_KEYWORDS.items():
        if any(keyword.lower() in lower for keyword in keywords):
            directions.append(direction)
    return directions or ["general-research"]


def detect_datasets(text: str) -> list[dict[str, str]]:
    found: dict[str, str] = {}
    for dataset in COMMON_DATASETS:
        if re.search(rf"\b{re.escape(dataset)}\b", text, flags=re.I):
            found[dataset] = dataset

    pattern = re.compile(r"\b([A-Z][A-Za-z0-9_-]{2,}(?:\s+[A-Z][A-Za-z0-9_-]{2,}){0,3})\s+(dataset|corpus|benchmark)\b")
    for match in pattern.finditer(text):
        name = match.group(1).strip()
        if len(name) <= 60:
            found[name] = match.group(0)
    return [{"name": name, "evidence": evidence} for name, evidence in sorted(found.items())]


def detect_metrics(text: str) -> list[dict[str, str]]:
    lower = text.lower()
    metrics: list[dict[str, str]] = []
    for metric in COMMON_METRICS:
        if re.search(rf"\b{re.escape(metric)}\b", lower):
            metrics.append({"name": metric.upper() if len(metric) <= 4 else metric, "evidence": metric})
    return metrics


def infer_innovation_type(sentence: str) -> str:
    lower = sentence.lower()
    if any(k in lower for k in ["dataset", "benchmark", "corpus"]):
        return "data"
    if any(k in lower for k in ["loss", "objective", "regularization", "optimization"]):
        return "objective"
    if any(k in lower for k in ["architecture", "network", "module", "framework", "model"]):
        return "architecture"
    if any(k in lower for k in ["evaluation", "metric", "experiment", "benchmark"]):
        return "evaluation"
    return "method"


def collect_limitations(sections: dict[str, str]) -> list[dict[str, str]]:
    explicit: list[dict[str, str]] = []
    for name in ["Limitations", "Future Work"]:
        if sections.get(name):
            for sentence in split_sentences(sections[name])[:6]:
                explicit.append({"text": sentence, "evidence": name})
    keyword_based = find_keyword_sentences(sections, LIMITATION_KEYWORDS, max_items=6)

    seen: set[str] = set()
    merged: list[dict[str, str]] = []
    for item in explicit + keyword_based:
        key = item["text"].lower()
        if key not in seen:
            seen.add(key)
            merged.append(item)
    return merged[:8]


def analyze_paper(extracted: dict[str, Any]) -> dict[str, Any]:
    sections = extracted.get("sections") or {}
    if extracted.get("status") != "ok":
        return {
            "paperId": extracted["paperId"],
            "title": extracted.get("title", ""),
            "status": "failed",
            "error": extracted.get("error"),
            "problem": "",
            "coreIdea": "",
            "keyInnovations": [],
            "methods": [],
            "datasets": [],
            "metrics": [],
            "limitations": [],
            "futureWork": [],
            "directions": [],
            "confidence": "none",
        }

    combined = text_for_analysis(extracted)
    abstract = sections.get("Abstract", "")
    introduction = sections.get("Introduction", "")
    method = sections.get("Method", "")
    conclusion = sections.get("Conclusion", "")

    innovation_sentences = find_keyword_sentences(
        sections,
        INNOVATION_KEYWORDS,
        max_items=8,
        skip_sections={"Limitations", "Future Work", "References"},
    )
    innovations = [
        {
            "id": f"claim:{extracted['paperId'].split(':', 1)[-1]}:{slugify(item['text'][:60], 'innovation')}",
            "text": item["text"],
            "evidence": item["evidence"],
            "innovationType": infer_innovation_type(item["text"]),
        }
        for item in innovation_sentences
    ]

    limitations = collect_limitations(sections)
    future_work = [
        item
        for item in limitations
        if "future" in item["text"].lower() or item["evidence"] == "Future Work" or "未来" in item["text"]
    ]

    methods = detect_methods(combined)
    directions = detect_directions(combined)

    if innovations and len(combined) > 1500:
        confidence = "medium"
    elif len(combined) > 500:
        confidence = "low"
    else:
        confidence = "very-low"

    return {
        "paperId": extracted["paperId"],
        "title": extracted.get("title", ""),
        "status": "ok",
        "error": None,
        "problem": first_sentences(introduction or abstract, 2),
        "coreIdea": first_sentences(method or abstract or conclusion, 2),
        "keyInnovations": innovations,
        "methods": methods,
        "datasets": detect_datasets(combined),
        "metrics": detect_metrics(combined),
        "limitations": limitations,
        "futureWork": future_work[:5],
        "directions": directions,
        "confidence": confidence,
        "textLength": extracted.get("textLength", 0),
    }


def analyze_all(extracted_items: list[dict[str, Any]]) -> dict[str, Any]:
    papers = [analyze_paper(item) for item in extracted_items]
    direction_counts = Counter(direction for paper in papers for direction in paper.get("directions", []))
    method_counts = Counter(method["name"] for paper in papers for method in paper.get("methods", []))

    cooccurrence: dict[str, Counter[str]] = defaultdict(Counter)
    for paper in papers:
        directions = paper.get("directions", [])
        methods = [method["name"] for method in paper.get("methods", [])]
        for direction in directions:
            for method in methods:
                cooccurrence[direction][method] += 1

    trends = []
    for direction, count in direction_counts.most_common():
        top_methods = [name for name, _ in cooccurrence[direction].most_common(5)]
        trends.append(
            {
                "direction": direction,
                "paperCount": count,
                "topMethods": top_methods,
                "maturity": "mainstream" if count >= 3 else "emerging" if count == 2 else "underexplored",
            }
        )

    gaps = infer_gaps(papers, direction_counts, method_counts)
    methodology_suggestions = propose_methodologies(trends, gaps, method_counts)

    return {
        "papers": papers,
        "trends": trends,
        "gaps": gaps,
        "methodologySuggestions": methodology_suggestions,
        "stats": {
            "paperCount": len(papers),
            "successfulAnalyses": sum(1 for paper in papers if paper.get("status") == "ok"),
            "failedAnalyses": sum(1 for paper in papers if paper.get("status") != "ok"),
            "directionCounts": dict(direction_counts),
            "methodCounts": dict(method_counts),
        },
    }


def infer_gaps(
    papers: list[dict[str, Any]],
    direction_counts: Counter[str],
    method_counts: Counter[str],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []

    limitation_terms = Counter()
    supporting: dict[str, set[str]] = defaultdict(set)
    term_patterns = [
        "scalability",
        "robustness",
        "interpretability",
        "generalization",
        "data scarcity",
        "annotation cost",
        "latency",
        "privacy",
        "bias",
        "hallucination",
        "evaluation",
    ]
    for paper in papers:
        for item in paper.get("limitations", []):
            text = item["text"].lower()
            for term in term_patterns:
                if term in text:
                    limitation_terms[term] += 1
                    supporting[term].add(paper["paperId"])

    for term, count in limitation_terms.most_common(5):
        gaps.append(
            {
                "name": f"Unresolved {term}",
                "type": "limitation-driven",
                "whyUnderexplored": f"{count} paper(s) mention {term} as a limitation or challenge.",
                "supportingPapers": sorted(supporting[term]),
                "risk": "medium",
                "potentialValue": "High if the limitation appears across multiple methods or tasks.",
            }
        )

    for direction, count in direction_counts.items():
        if count == 1 and direction != "general-research":
            papers_in_direction = [
                paper["paperId"] for paper in papers if direction in paper.get("directions", [])
            ]
            gaps.append(
                {
                    "name": f"Underexplored direction: {direction}",
                    "type": "low-coverage-direction",
                    "whyUnderexplored": "Only one paper in the local corpus is mapped to this direction.",
                    "supportingPapers": papers_in_direction,
                    "risk": "high",
                    "potentialValue": "May be valuable if this local corpus reflects the target research niche.",
                }
            )

    if method_counts:
        rare_methods = [name for name, count in method_counts.items() if count == 1]
        common_methods = [name for name, count in method_counts.items() if count >= 2]
        if rare_methods and common_methods:
            gaps.append(
                {
                    "name": "Sparse method combination space",
                    "type": "method-combination",
                    "whyUnderexplored": "Some methods appear in isolation and may be combinable with mainstream methods.",
                    "supportingPapers": [],
                    "rareMethods": rare_methods[:5],
                    "commonMethods": common_methods[:5],
                    "risk": "medium",
                    "potentialValue": "Potential source of method innovation through cross-pollination.",
                }
            )

    return gaps[:10]


def propose_methodologies(
    trends: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    method_counts: Counter[str],
) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    top_methods = [name for name, _ in method_counts.most_common(5)]
    mainstream = [trend for trend in trends if trend["maturity"] == "mainstream"]
    emerging = [trend for trend in trends if trend["maturity"] != "mainstream"]

    if mainstream and emerging:
        suggestions.append(
            {
                "title": "Bridge a mainstream direction with an underexplored direction",
                "basis": "Inferred",
                "idea": (
                    f"Combine {mainstream[0]['direction']} with {emerging[0]['direction']} "
                    "and evaluate whether mature techniques transfer to the lower-coverage setting."
                ),
                "candidateMethods": list(dict.fromkeys(mainstream[0].get("topMethods", []) + emerging[0].get("topMethods", [])))[:5],
                "experimentSketch": "Use representative baselines from the mainstream direction and run ablations on the transferred component.",
            }
        )

    if gaps:
        suggestions.append(
            {
                "title": "Target the most repeated limitation",
                "basis": "Evidence-based" if gaps[0]["type"] == "limitation-driven" else "Inferred",
                "idea": f"Design a method specifically around: {gaps[0]['name']}.",
                "candidateMethods": top_methods,
                "experimentSketch": "Build a benchmark slice that isolates this limitation and compare against the most frequent local methods.",
            }
        )

    if len(top_methods) >= 2:
        suggestions.append(
            {
                "title": "Create a compositional method baseline",
                "basis": "Speculative",
                "idea": f"Prototype a hybrid method combining {top_methods[0]} and {top_methods[1]}.",
                "candidateMethods": top_methods[:3],
                "experimentSketch": "Run component-level ablation to show whether the combination improves over each method alone.",
            }
        )

    if not suggestions:
        suggestions.append(
            {
                "title": "Expand the corpus before proposing method innovation",
                "basis": "Evidence-based",
                "idea": "The current corpus has too little analyzable signal for reliable gap discovery.",
                "candidateMethods": [],
                "experimentSketch": "Add more papers from the same target venue or topic and rerun the analysis.",
            }
        )

    return suggestions
