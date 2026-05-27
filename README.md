# Paper Research Assistant

Understand Anything style skill for research-paper corpora.

This project is intentionally split into two roles:

- **Python** scans papers, extracts text, prepares batches, validates/merges JSON, and builds the final graph/report.
- **Host model** such as Codex reads extracted paper text and performs semantic analysis.

Python does not call OpenAI, Anthropic, or any other model API directly.

## Host Skill Workflow

Prepare extracted text and batch manifests:

```powershell
cd D:\project\paper-research-assistant
python -m paper_research_assistant prepare D:\path\to\papers --force
```

For routine incremental runs, omit `--force`:

```powershell
python -m paper_research_assistant prepare D:\path\to\papers
```

`prepare` compares each paper's `sha256` with existing `paper-analysis-*.json` files. Codex should only read papers listed in `intermediate\analysis-batches.json` `batches[].papers`; unchanged papers are listed as cached and are not re-read.

The host model then reads:

```text
D:\path\to\papers\.paper-research-assistant\intermediate\analysis-batches.json
```

and writes:

```text
paper-analysis-1.json
paper-analysis-2.json
...
corpus-analysis.json
```

Finalize graph and report:

```powershell
python -m paper_research_assistant finalize D:\path\to\papers
```

## Outputs

The final analysis artifacts are:

```text
D:\path\to\papers\.paper-research-assistant\
  literature-graph.json
  research-map-report.md
```

Other files in `.paper-research-assistant` are cache, merged analysis, or intermediate workflow files.

## Dashboard

The dashboard is a read-only viewer for the graph, paper summaries, trends, gaps, and methodology suggestions.

```powershell
python -m paper_research_assistant dashboard D:\path\to\papers
```

It starts a React/Vite local web app. It requires Node.js with npm.

## PDF Dependency

For PDF extraction, install one:

```powershell
python -m pip install pymupdf
```

or:

```powershell
python -m pip install pypdf
```

## Local Smoke Test

This command exists only to verify the deterministic pipeline:

```powershell
python -m paper_research_assistant analyze D:\path\to\papers
```

It uses heuristic extraction and is not the intended skill workflow.
