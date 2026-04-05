"""
Saver node — persists all run artifacts to disk.

Writes:
  - trace.json       — full state snapshot (for reproducibility / ablation)
  - report.md        — markdown rendering of the structured Report
  - metadata.json    — run timings and LLM config snapshot

PDF conversion (report.md → report.pdf) is attempted via pandoc if installed;
failure is silent so missing pandoc doesn't break the pipeline.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from pydantic import BaseModel

from sparq.schemas.state import State


def _pydantic_encoder(obj):
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def _report_to_markdown(state: State) -> str:
    report = state.get("report")
    query = state.get("query", "")

    if report is None:
        return f"# No Report Generated\n\n**Query:** {query}\n"

    figures = state.get("research_log", [])
    all_figures = []
    for entry in figures:
        all_figures.extend(entry.figures_generated)

    md = f"# {report.title}\n\n"
    md += f"**Original query:** {query}\n\n"
    md += f"## Abstract\n\n{report.abstract}\n\n"
    md += f"## Methods\n\n{report.methods}\n\n"
    md += f"## Results\n\n{report.results}\n\n"

    if all_figures:
        md += "### Figures\n\n"
        for i, fig in enumerate(all_figures, start=1):
            md += f"**Figure {i}:** {fig}\n\n"

    md += f"## Discussion\n\n{report.discussion}\n\n"
    md += f"## Conclusion\n\n{report.conclusion}\n\n"
    md += f"## Limitations\n\n{report.limitations}\n"

    return md


def saver_node(state: State, save_dir: Path) -> dict:
    save_dir.mkdir(parents=True, exist_ok=True)

    # --- trace.json ---
    with open(save_dir / "trace.json", "w") as f:
        json.dump(dict(state), f, indent=4, default=_pydantic_encoder)

    # --- report.md ---
    md_path = save_dir / "report.md"
    md_path.write_text(_report_to_markdown(state), encoding="utf-8")

    # --- metadata.json ---
    run_metadata = state.get("run_metadata")
    if run_metadata is not None:
        with open(save_dir / "metadata.json", "w") as f:
            json.dump(_pydantic_encoder(run_metadata), f, indent=4)

    # --- report.pdf (best-effort) ---
    try:
        subprocess.run(
            ["pandoc", str(md_path), "-o", str(save_dir / "report.pdf")],
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        pass  # pandoc not installed or failed — markdown is still saved

    return {}
