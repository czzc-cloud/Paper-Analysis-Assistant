---
name: paper-research-assistant
description: Use host-model analysis to read a local folder of research papers, extract innovations and methods, build a literature knowledge graph, discover research gaps, and propose method innovation ideas.
---

# Paper Research Assistant

Use this skill when the user asks to analyze a local research-paper folder, literature corpus, PDF collection, research direction, or method landscape.

This skill follows the Understand Anything pattern:

- Python handles deterministic work: scan files, extract PDF/text, write batch manifests, validate and merge JSON, build graph/report.
- The host model handles semantic work: read extracted paper text, identify innovations/methods/limitations, synthesize research directions and gaps.
- Python does not call an external model API.

## Outputs

Default output directory:

```text
<paper-folder>/.paper-research-assistant/
```

Files:

- `papers.json` - scanned paper manifest
- `paper-text/*.json` - extracted text and detected sections
- `intermediate/analysis-batches.json` - batch manifest for host-model analysis
- `intermediate/paper-analysis-<N>.json` - per-batch semantic analysis written by the host model
- `intermediate/corpus-analysis.json` - optional cross-paper synthesis written by the host model
- `analysis.json` - merged analysis
- `literature-graph.json` - final literature knowledge graph deliverable, including dashboard-ready insights
- `research-map-report.md` - final research report deliverable
- `run-summary.json` - run status and paths

The final user-facing artifacts are:

- `research-map-report.md`
- `literature-graph.json`
- the local dashboard viewer after analysis is complete

The dashboard reads `literature-graph.json`, `analysis.json`, and `research-map-report.md`. It is the preferred final presentation surface, but the files remain the source of truth.

Incremental behavior:

- `prepare` scans the current folder and compares each paper's `sha256` against existing host-model analyses.
- Papers listed in `cachedPaperIds` already have matching analysis and must not be re-read by the host model.
- Only papers in `batches[].papers` need semantic analysis.
- If a PDF is edited or replaced, its hash changes and it becomes pending again.

## Workflow

### Phase 0: Resolve Paths

Set `PAPER_DIR` from the user's argument or current working directory.
Use this repository or installed skill directory as `SKILL_ROOT`.

### Phase 1: Prepare

Run:

```bash
cd <SKILL_ROOT>
python -m paper_research_assistant prepare <PAPER_DIR>
```

If the user requests a smaller run, add `--limit <N>`.
If PDF extraction cache is stale or dependencies were just installed, add `--force`.

If PDF extraction fails because dependencies are missing, tell the user to install one of:

```bash
python -m pip install pymupdf
python -m pip install pypdf
```

Stop if `run-summary.json` shows `successfulExtractions` is `0`.

After prepare, read `run-summary.json`:

- If `pendingAnalyses` is `0`, skip Phase 2. Existing paper analyses are up to date.
- If `pendingAnalyses` is greater than `0`, analyze only the papers listed in `analysis-batches.json` `batches[].papers`.

### Phase 2: Batch Paper Analysis

Read:

```text
<PAPER_DIR>/.paper-research-assistant/intermediate/analysis-batches.json
```

For each batch:

1. Read the `textPath` for every paper in the batch.
2. Use `agents/paper-analyzer.md` as the analysis contract.
3. Write:

```text
<PAPER_DIR>/.paper-research-assistant/intermediate/paper-analysis-<batchIndex>.json
```

The file must have this shape:

```json
{
  "papers": [
    {
      "paperId": "paper:example",
      "sourceHash": "<copy sourceHash from the batch manifest>",
      "title": "Example Paper",
      "status": "ok",
      "problem": "...",
      "coreIdea": "...",
      "keyInnovations": [
        {"text": "...", "evidence": "Abstract", "innovationType": "method"}
      ],
      "methods": [
        {"name": "contrastive learning", "evidence": "Method"}
      ],
      "datasets": [],
      "metrics": [],
      "limitations": [],
      "futureWork": [],
      "directions": [],
      "confidence": "high|medium|low"
    }
  ]
}
```

Every claim should cite a section name or short evidence string. Do not invent details that are not grounded in extracted text.
Use `directions` only for broad research areas, tasks, or application domains such as `person-re-identification`, `image-retrieval`, `image-segmentation`, or `medical-imaging`; put reusable techniques such as contrastive learning, hashing, distillation, pseudo-labeling, and attention in `methods`.
Copy `sourceHash` exactly. It is used to avoid re-reading unchanged papers on later runs.

### Phase 3: Corpus Synthesis

After all `paper-analysis-*.json` files exist, read them and use `agents/corpus-synthesizer.md`.
For incremental runs, include both cached old analyses and newly written analyses in the synthesis.

Write:

```text
<PAPER_DIR>/.paper-research-assistant/intermediate/corpus-analysis.json
```

Shape:

```json
{
  "trends": [
    {"direction": "...", "paperCount": 3, "topMethods": ["..."], "maturity": "mainstream|emerging|underexplored"}
  ],
  "gaps": [
    {
      "name": "...",
      "type": "limitation-driven|low-coverage-direction|method-combination|evaluation-gap",
      "whyUnderexplored": "...",
      "supportingPapers": ["paper:..."],
      "risk": "low|medium|high",
      "potentialValue": "..."
    }
  ],
  "methodologySuggestions": [
    {
      "title": "...",
      "basis": "Evidence-based|Inferred|Speculative",
      "idea": "...",
      "candidateMethods": ["..."],
      "experimentSketch": "..."
    }
  ]
}
```

### Phase 4: Finalize

Run:

```bash
cd <SKILL_ROOT>
python -m paper_research_assistant finalize <PAPER_DIR>
```

This validates and merges host-model JSON, then writes `analysis.json`, `literature-graph.json`, `research-map-report.md`, and `run-summary.json`.

### Phase 5: Report To User

Read `run-summary.json` and summarize:

- papers scanned
- paper analyses merged
- graph node/edge counts
- paths to `literature-graph.json` and `research-map-report.md`
- any failed PDFs or low-confidence analyses

### Phase 6: Launch Dashboard

Launch the dashboard after a successful `finalize` unless the user explicitly asked not to open a viewer.

Run:

```bash
cd <SKILL_ROOT>
python -m paper_research_assistant dashboard <PAPER_DIR>
```

This starts a React/Vite local viewer for the graph, paper summaries, trends, gaps, and methodology suggestions. It does not create or change the final graph/report.
If `npm` is missing, tell the user to install Node.js with npm.

When working inside Codex, start the dashboard as a background process if needed, then open `http://127.0.0.1:5179` in the in-app browser. If port `5179` is unavailable, pass another `--port` value and open that URL.

## Notes

- Do not manually read raw PDF files in the model context. Always use `prepare` first and read `paper-text/*.json`.
- Do not read cached papers again. `analysis-batches.json` is the authority for which papers need host-model analysis.
- Do not call OpenAI/Anthropic APIs from Python. The host model is the semantic analyzer.
- The `analyze` CLI command is only a local heuristic smoke test. The skill workflow must use `prepare` and `finalize`.
- The dashboard is read-only. Do not let it become the source of truth; `literature-graph.json` remains the graph artifact.
