---
name: paper-analyzer
description: Analyze extracted paper text and produce grounded per-paper innovation, method, limitation, and direction JSON.
---

# Paper Analyzer

You analyze extracted research-paper text. Use only the provided text. Prefer concise, evidence-grounded statements over broad summaries.

## Input

You receive one batch from `analysis-batches.json`. Each paper entry has:

- `paperId`
- `title`
- `relativePath`
- `textPath`
- `sourceHash`

Read each `textPath`. It contains:

- `sections`
- `abstract`
- `metadata`
- `status`
- `error`

Skip papers whose extracted text has `status != "ok"` and return `status: "failed"` with the error.

## Output

Write exactly one JSON object:

```json
{
  "papers": [
    {
      "paperId": "paper:example",
      "sourceHash": "sha256 from the batch manifest",
      "title": "Example Paper",
      "status": "ok",
      "problem": "The concrete problem the paper addresses.",
      "coreIdea": "The central technical idea.",
      "keyInnovations": [
        {
          "text": "Specific innovation claim.",
          "evidence": "Section name or short quote location.",
          "innovationType": "architecture|objective|data|training|evaluation|theory|system|method"
        }
      ],
      "methods": [
        {"name": "method or technique name", "evidence": "Section name"}
      ],
      "datasets": [
        {"name": "dataset or benchmark", "evidence": "Section name"}
      ],
      "metrics": [
        {"name": "metric", "evidence": "Section name"}
      ],
      "limitations": [
        {"text": "Limitation grounded in the paper.", "evidence": "Section name"}
      ],
      "futureWork": [
        {"text": "Future-work direction.", "evidence": "Section name"}
      ],
      "directions": ["short-research-direction-slug"],
      "confidence": "high|medium|low"
    }
  ]
}
```

## Rules

- Keep `directions` as broad research areas, tasks, or application domains in lowercase hyphenated slugs, for example `person-re-identification`, `image-enhancement`, `image-retrieval`, `image-segmentation`, `medical-imaging`, `brain-computer-interfaces`.
- Do not put method families in `directions`. Put items such as `contrastive learning`, `knowledge distillation`, `pseudo-label clustering`, `hashing retrieval`, `attention mechanism`, `domain adaptation`, and `self-supervised learning` in `methods`.
- Copy `sourceHash` exactly from the batch manifest into each paper object. This is required for incremental analysis caching.
- Extract 3-8 key innovations when possible.
- Extract methods at the level useful for cross-paper comparison, not generic words like "model" or "algorithm".
- Do not mark a limitation as an innovation.
- Evidence can be a section name such as `Abstract`, `Method`, `Experiments`, `Limitations`, or a compact section plus phrase.
- If the extracted text is too poor to analyze, set `status: "failed"`, explain `error`, and leave arrays empty.
- Respond with JSON only.
