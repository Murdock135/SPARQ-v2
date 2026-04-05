"""
Ablation runner.

Runs SPARQ on a fixed question under multiple configuration overrides and
compares the results. Produces a table suitable for inclusion in a paper.

Usage:
    uv run python -m sparq.eval.ablation

Ablation configs are defined in ABLATION_CONFIGS below. Each entry is a
dict of TOML-path overrides applied on top of the base config.

Example:
    {"llm_config.researcher.model": "gemini-2.0-flash"}  # baseline
    {"llm_config.researcher.model": "gemini-2.5-pro"}    # stronger model

    Or to ablate the critic:
    {} # with critic (baseline)
    {"ablation.disable_critic": True}  # without critic loop
"""

from __future__ import annotations

import asyncio
import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from sparq.eval.judge import judge_report
from sparq.schemas.output_schemas import Judgement, Report
from sparq.settings import AgenticSystemSettings, ENVSettings

_EVAL_OUTPUT_DIR = Path.home() / "tmp" / "sparq_v2" / "eval" / "ablation"

# ---------------------------------------------------------------------------
# Define your ablation configurations here.
# Each entry: {"label": "...", "overrides": {dot-path: value, ...}}
# ---------------------------------------------------------------------------
ABLATION_CONFIGS: list[dict] = [
    {
        "label": "baseline",
        "overrides": {},
    },
    {
        "label": "no_critic",
        "overrides": {"ablation.disable_critic": True},
    },
    {
        "label": "no_vision",
        "overrides": {"ablation.disable_vision": True},
    },
    {
        "label": "planner_flash",
        "overrides": {
            "llm_config.planner.model": "gemini-2.0-flash",
            "llm_config.planner.provider": "google_genai",
        },
    },
    {
        "label": "researcher_flash",
        "overrides": {
            "llm_config.researcher.model": "gemini-2.0-flash",
            "llm_config.researcher.provider": "google_genai",
        },
    },
]

# Test question for ablation (picked to be representative and grade-3+)
ABLATION_QUESTION = (
    "Which specific demographic groups in our service area face the highest combined "
    "risk from food insecurity and Salmonella exposure?"
)


def _apply_overrides(settings: AgenticSystemSettings, overrides: dict[str, Any]) -> None:
    """Apply dot-path overrides to a settings object in-place (best-effort)."""
    for path, value in overrides.items():
        parts = path.split(".")
        obj = settings
        for part in parts[:-1]:
            if hasattr(obj, part):
                obj = getattr(obj, part)
            else:
                break
        else:
            if hasattr(obj, parts[-1]):
                try:
                    setattr(obj, parts[-1], value)
                except Exception:
                    pass


async def run_ablation(
    question: str = ABLATION_QUESTION,
    configs: list[dict] | None = None,
) -> None:
    ENVSettings()
    configs = configs or ABLATION_CONFIGS
    _EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Running ablation study on {len(configs)} configuration(s)...")
    print(f"Question: {question[:80]}...\n")

    results = []

    for cfg_entry in configs:
        label = cfg_entry["label"]
        overrides = cfg_entry.get("overrides", {})
        print(f"  Running: {label} {overrides or ''}")

        try:
            from sparq.system import AgenticSystem
            system = AgenticSystem()
            _apply_overrides(system.settings, overrides)

            await system.run(question)

            run_dir = system.settings.paths.run_dir
            trace_path = run_dir / "trace.json"

            score: dict | None = None
            if trace_path.exists():
                with open(trace_path) as f:
                    trace = json.load(f)
                report_dict = trace.get("report")
                if report_dict:
                    report = Report(**report_dict)
                    judge_cfg = system.settings.llm_config.synthesizer
                    judgement = judge_report(question, report, judge_cfg)
                    score = {
                        "relevance": judgement.relevance,
                        "completeness": judgement.completeness,
                        "scientific_validity": judgement.scientific_validity,
                        "clarity": judgement.clarity,
                        "total": judgement.total,
                        "rationale": judgement.rationale,
                    }

            results.append({
                "label": label,
                "overrides": overrides,
                "run_dir": str(run_dir),
                "scores": score,
                "status": "ok" if score else "no_report",
            })

        except Exception as e:
            results.append({"label": label, "status": "error", "error": str(e)})
            print(f"    ERROR: {e}")

    # Write results
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    output_path = _EVAL_OUTPUT_DIR / f"ablation_{timestamp}.json"
    with open(output_path, "w") as f:
        json.dump({"question": question, "timestamp": timestamp, "results": results}, f, indent=4)

    print(f"\nResults written to {output_path}")
    _print_ablation_table(results)


def _print_ablation_table(results: list[dict]) -> None:
    print(f"\n{'Label':<25} {'Rel':>4} {'Comp':>5} {'Val':>4} {'Clar':>5} {'Total':>6}")
    print("-" * 55)
    for r in results:
        s = r.get("scores") or {}
        label = r["label"]
        if s:
            print(f"{label:<25} {s['relevance']:>4} {s['completeness']:>5} "
                  f"{s['scientific_validity']:>4} {s['clarity']:>5} {s['total']:>6}")
        else:
            print(f"{label:<25} {'--':>4} {'--':>5} {'--':>4} {'--':>5} {r.get('status','?'):>6}")


if __name__ == "__main__":
    asyncio.run(run_ablation())
