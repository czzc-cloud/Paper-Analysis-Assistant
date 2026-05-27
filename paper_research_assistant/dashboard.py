from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from .scanner import OUTPUT_DIR_NAME


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_graph_file(paper_dir: Path, output_dir: Path | None = None) -> Path:
    root = output_dir.resolve() if output_dir else paper_dir.resolve() / OUTPUT_DIR_NAME
    graph_file = root / "literature-graph.json"
    if not graph_file.exists():
        raise FileNotFoundError(
            f"Knowledge graph not found: {graph_file}. Run finalize first."
        )
    return graph_file


def find_npm() -> Path:
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if npm:
        return Path(npm)

    candidates = [
        Path("C:/Program Files/nodejs/npm.cmd"),
        Path("C:/Program Files (x86)/nodejs/npm.cmd"),
        Path.home() / "AppData/Local/Programs/nodejs/npm.cmd",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise RuntimeError(
        "npm was not found on PATH or standard Node.js install locations. "
        "Install Node.js with npm, then rerun the dashboard command."
    )


def start_dashboard(
    paper_dir: Path,
    output_dir: Path | None = None,
    host: str = "127.0.0.1",
    port: int = 5179,
    install: bool = True,
) -> int:
    dashboard_dir = project_root() / "dashboard"
    if not dashboard_dir.exists():
        raise FileNotFoundError(f"Dashboard directory not found: {dashboard_dir}")

    graph_file = resolve_graph_file(paper_dir, output_dir=output_dir)
    npm = find_npm()
    node_dir = str(npm.parent)

    env = os.environ.copy()
    env["PATH"] = f"{node_dir}{os.pathsep}{env.get('PATH', '')}"

    if install and not (dashboard_dir / "node_modules").exists():
        install_result = subprocess.run([str(npm), "install"], cwd=dashboard_dir, env=env)
        if install_result.returncode != 0:
            return install_result.returncode

    env["PRA_GRAPH_FILE"] = str(graph_file)
    env["PRA_ANALYSIS_FILE"] = str(graph_file.parent / "analysis.json")
    env["PRA_REPORT_FILE"] = str(graph_file.parent / "research-map-report.md")

    return subprocess.call(
        [str(npm), "run", "dev", "--", "--host", host, "--port", str(port)],
        cwd=dashboard_dir,
        env=env,
    )
