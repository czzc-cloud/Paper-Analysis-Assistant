from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .dashboard import start_dashboard
from .host_workflow import finalize_host_analysis, prepare_host_analysis
from .pipeline import analyze_directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="paper-research-assistant",
        description="Analyze local papers into a literature knowledge graph and research map report.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare",
        help="Prepare paper text and batch manifests for host-model analysis",
    )
    prepare.add_argument("paper_dir", type=Path, help="Folder containing PDF, TXT, or Markdown papers")
    prepare.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to <paper_dir>/.paper-research-assistant",
    )
    prepare.add_argument("--force", action="store_true", help="Re-extract cached paper text")
    prepare.add_argument("--limit", type=int, default=None, help="Prepare at most N papers")
    prepare.add_argument("--batch-size", type=int, default=4, help="Papers per host-model analysis batch")

    finalize = subparsers.add_parser(
        "finalize",
        help="Merge host-model paper-analysis JSON files into graph and report",
    )
    finalize.add_argument("paper_dir", type=Path, help="Folder containing prepared outputs")
    finalize.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to <paper_dir>/.paper-research-assistant",
    )
    finalize.add_argument(
        "--allow-partial",
        action="store_true",
        help="Finalize even when no host analysis files are present",
    )

    analyze = subparsers.add_parser("analyze", help="Local heuristic smoke test; skill workflow should use prepare/finalize")
    analyze.add_argument("paper_dir", type=Path, help="Folder containing PDF, TXT, or Markdown papers")
    analyze.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to <paper_dir>/.paper-research-assistant",
    )
    analyze.add_argument("--force", action="store_true", help="Re-extract cached paper text")
    analyze.add_argument("--limit", type=int, default=None, help="Analyze at most N papers")

    dashboard = subparsers.add_parser("dashboard", help="Start the React/Vite graph dashboard")
    dashboard.add_argument("paper_dir", type=Path, help="Folder containing .paper-research-assistant outputs")
    dashboard.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to <paper_dir>/.paper-research-assistant",
    )
    dashboard.add_argument("--host", default="127.0.0.1", help="Dashboard host")
    dashboard.add_argument("--port", type=int, default=5179, help="Dashboard port")
    dashboard.add_argument(
        "--no-install",
        action="store_true",
        help="Do not run npm install before starting Vite",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "prepare":
            summary = prepare_host_analysis(
                paper_dir=args.paper_dir,
                output_dir=args.output_dir,
                force=args.force,
                limit=args.limit,
                batch_size=args.batch_size,
            )
            print("Paper Research Assistant prepare complete.")
            print(f"Papers scanned: {summary['papersScanned']}")
            print(f"Successful extractions: {summary['successfulExtractions']}")
            print(f"Failed extractions: {summary['failedExtractions']}")
            print(f"Cached analyses: {summary['cachedAnalyses']}")
            print(f"Pending analyses: {summary['pendingAnalyses']}")
            print(f"Batches: {summary['batches']}")
            print(f"Batch manifest: {summary['outputs']['batches']}")
            return 0

        if args.command == "finalize":
            summary = finalize_host_analysis(
                paper_dir=args.paper_dir,
                output_dir=args.output_dir,
                allow_partial=args.allow_partial,
            )
            print("Paper Research Assistant finalize complete.")
            print(f"Paper analyses: {summary['paperAnalyses']}")
            print(f"Knowledge graph: {summary['outputs']['graph']}")
            print(f"Research report: {summary['outputs']['report']}")
            return 0

        if args.command == "analyze":
            summary = analyze_directory(
                paper_dir=args.paper_dir,
                output_dir=args.output_dir,
                force=args.force,
                limit=args.limit,
            )
            print("Paper Research Assistant analysis complete.")
            print(f"Papers scanned: {summary['papersScanned']}")
            print(f"Successful extractions: {summary['successfulExtractions']}")
            print(f"Failed extractions: {summary['failedExtractions']}")
            print(f"Knowledge graph: {summary['outputs']['graph']}")
            print(f"Research report: {summary['outputs']['report']}")
            return 0

        if args.command == "dashboard":
            return start_dashboard(
                paper_dir=args.paper_dir,
                output_dir=args.output_dir,
                host=args.host,
                port=args.port,
                install=not args.no_install,
            )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    parser.print_help()
    return 1
