# One Summary to Rule Them All Workflow

This project is designed as an Understand Anything style skill:

- The skill workflow is executed by a host model such as Codex.
- Python scripts perform deterministic file and graph work.
- The host model performs semantic paper analysis.
- Python does not call a model API directly.

## Goal

Given a local folder of papers, produce:

- extracted paper text
- structured per-paper innovation and method analysis
- a literature knowledge graph
- research-gap analysis
- method innovation suggestions
- a human-readable research map report

## Output Layout

```text
<paper-folder>/.paper-research-assistant/
  papers.json
  paper-text/
  intermediate/
    analysis-batches.json
    paper-analysis-1.json
    paper-analysis-2.json
    corpus-analysis.json
  analysis.json
  literature-graph.json
  research-map-report.md
  run-summary.json
```

Final user-facing deliverables:

- `research-map-report.md`
- `literature-graph.json`
- local dashboard viewer

The dashboard reads `literature-graph.json`, `analysis.json`, and `research-map-report.md` to present the final research map, paper summaries, gaps, innovation ideas, and graph exploration view.

## Execution Modes

The project supports two distinct modes.

### Codex Skill Mode

This is the intended assistant workflow. The user can ask Codex:

```text
Use this skill to study all papers under D:\papers, generate the literature analysis, and open the dashboard.
```

Codex then orchestrates the full chain:

```text
prepare -> batch paper analysis -> corpus synthesis -> finalize -> dashboard
```

In this mode, Codex reads `analysis-batches.json`, analyzes the pending `paper-text/*.json` files, writes `paper-analysis-<N>.json` and `corpus-analysis.json`, runs `finalize`, starts the dashboard, and opens the local page.

### Manual CLI Mode

This mode is for step-by-step control and debugging. The Python CLI can prepare, finalize, and serve the dashboard, but it does not perform final semantic research analysis by itself.

Manual users must provide the semantic JSON files before finalization:

```text
intermediate/paper-analysis-<N>.json
intermediate/corpus-analysis.json
```

The deterministic local `analyze` command is only a smoke test and should not be treated as the final literature-review workflow.

## Phase 1: Prepare

Python command:

```bash
python -m paper_research_assistant prepare <paper-folder> --force
```

Responsibilities:

- scan `.pdf`, `.txt`, `.md`
- compute SHA256
- extract PDF/text content
- split common paper sections
- write `papers.json`
- write `paper-text/*.json`
- write `intermediate/analysis-batches.json`
- compare current paper hashes with existing `paper-analysis-*.json`
- mark unchanged papers as cached
- include only new or changed papers in `batches[].papers`

No semantic research claims are made in this phase.

For routine incremental runs, omit `--force`:

```bash
python -m paper_research_assistant prepare <paper-folder>
```

Use `--force` only when text extraction cache should be regenerated.

## Phase 2: Host Paper Analysis

The host model reads each batch from `analysis-batches.json`.
It must not re-read papers listed in `cachedPaperIds`.

For every paper in the batch:

- read its `textPath`
- extract problem, core idea, innovations, methods, datasets, metrics, limitations, future work, directions
- keep `directions` for broad research areas/tasks/domains and keep reusable technical approaches in `methods`
- copy `sourceHash` into the output
- write `intermediate/paper-analysis-<batchIndex>.json`

Contract: `agents/paper-analyzer.md`.

## Phase 3: Host Corpus Synthesis

The host model reads all current `paper-analysis-*.json` files, including cached and newly written analyses, and writes:

```text
intermediate/corpus-analysis.json
```

It should identify:

- mainstream directions
- emerging directions
- underexplored gaps
- method-combination opportunities
- methodology suggestions

Contract: `agents/corpus-synthesizer.md`.

## Phase 4: Finalize

Python command:

```bash
python -m paper_research_assistant finalize <paper-folder>
```

Responsibilities:

- validate host-model JSON shape
- normalize paper-analysis objects
- merge corpus synthesis
- build `literature-graph.json`
- build `research-map-report.md`
- write `analysis.json`
- write `run-summary.json`

## Phase 5: Dashboard

React/Vite command:

```bash
python -m paper_research_assistant dashboard <paper-folder>
```

The dashboard reads the current `literature-graph.json` through `/api/graph`, `analysis.json` through `/api/analysis`, and the Markdown report through `/api/report`.

It is read-only and must not be treated as the source of truth.

## Graph Schema

Node types:

- `paper`
- `method`
- `direction`
- `gap`

Edge types:

- `belongs_to_direction`
- `uses_method_theme`
- `has_research_gap`
- `similar_method`
- `paper_overlap`

## Local Smoke Test

The CLI still exposes:

```bash
python -m paper_research_assistant analyze <paper-folder>
```

This is a heuristic local smoke test only. The skill workflow must use `prepare` and `finalize` so semantic analysis is performed by the host model.
