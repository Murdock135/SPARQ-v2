"""
Batch evaluation runner.

Runs SPARQ on all questions in data/Q_dataset.json, judges each Report with
LLM-as-judge, and writes a summary to output/eval/eval_results.json.

Usage:
    uv run python -m sparq.eval.batch
    uv run python -m sparq.eval.batch --questions 0 1 2   # specific indices
    uv run python -m sparq.eval.batch --grade-min 3       # only questions graded >= 3
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

from sparq.eval.judge import judge_report
from sparq.schemas.output_schemas import Judgement
from sparq.settings import AgenticSystemSettings, ENVSettings
from sparq.system import AgenticSystem

_Q_DATASET_PATH = Path(__file__).parents[4] / "data" / "Q_dataset.json"
_EVAL_OUTPUT_DIR = Path.home() / "tmp" / "sparq_v2" / "eval"


def _load_questions(
    grade_min: int | None = None,
    indices: list[int] | None = None,
) -> list[dict]:
    with open(_Q_DATASET_PATH) as f:
        data = json.load(f)
    questions = data["questions"]

    if indices is not None:
        questions = [questions[i] for i in indices]
    if grade_min is not None:
        questions = [q for q in questions if q.get("grade", 0) >= grade_min]
    return questions


async def _run_single(system: AgenticSystem, question: str) -> dict:
    """Run SPARQ on one question and return the final state."""
    run_id_states: list[dict] = []

    # Patch astream to capture final state
    async for chunk in system._build_graph(system.settings.paths.run_dir).astream(
        input={
            "query": question,
            "route": None,
            "direct_answer": None,
            "research_agenda": None,
            "data_context": None,
            "research_log": [],
            "critique": None,
            "revision_count": 0,
            "report": None,
            "run_id": "eval",
            "run_metadata": None,
        },
        stream_mode="updates",
    ):
        run_id_states.append(chunk)

    # Reconstruct final state from incremental updates
    final = {}
    for update in run_id_states:
        for node_output in update.values():
            if isinstance(node_output, dict):
                final.update(node_output)
    return final


async def run_batch(
    grade_min: int | None = None,
    indices: list[int] | None = None,
) -> None:
    ENVSettings()
    settings = AgenticSystemSettings()
    judge_cfg = settings.llm_config.synthesizer  # reuse synthesizer LLM for judging

    questions = _load_questions(grade_min=grade_min, indices=indices)
    print(f"Running batch evaluation on {len(questions)} question(s)...")

    _EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    for i, q in enumerate(questions):
        question_text = q["text"]
        expected_grade = q.get("grade")
        print(f"\n[{i+1}/{len(questions)}] {question_text[:80]}...")

        try:
            system = AgenticSystem()
            await system.run(question_text)

            # Load the report from the latest run_dir
            run_dir = system.settings.paths.run_dir
            trace_path = run_dir / "trace.json"
            if trace_path.exists():
                with open(trace_path) as f:
                    trace = json.load(f)
                report_dict = trace.get("report")
                if report_dict:
                    from sparq.schemas.output_schemas import Report
                    report = Report(**report_dict)
                    judgement = judge_report(question_text, report, judge_cfg)
                    result = {
                        "question": question_text,
                        "expected_grade": expected_grade,
                        "scores": {
                            "relevance": judgement.relevance,
                            "completeness": judgement.completeness,
                            "scientific_validity": judgement.scientific_validity,
                            "clarity": judgement.clarity,
                            "total": judgement.total,
                        },
                        "rationale": judgement.rationale,
                        "run_dir": str(run_dir),
                        "status": "ok",
                    }
                else:
                    result = {"question": question_text, "status": "no_report"}
            else:
                result = {"question": question_text, "status": "no_trace"}

        except Exception as e:
            result = {"question": question_text, "status": "error", "error": str(e)}
            print(f"  ERROR: {e}")

        results.append(result)

    # Write summary
    timestamp = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    output_path = _EVAL_OUTPUT_DIR / f"eval_results_{timestamp}.json"
    with open(output_path, "w") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "n_questions": len(questions),
                "results": results,
                "aggregate": _aggregate(results),
            },
            f,
            indent=4,
        )
    print(f"\nResults written to {output_path}")
    _print_summary(results)


def _aggregate(results: list[dict]) -> dict:
    ok = [r for r in results if r.get("status") == "ok"]
    if not ok:
        return {}
    keys = ["relevance", "completeness", "scientific_validity", "clarity", "total"]
    return {
        k: round(sum(r["scores"][k] for r in ok) / len(ok), 2)
        for k in keys
    }


def _print_summary(results: list[dict]) -> None:
    ok = [r for r in results if r.get("status") == "ok"]
    errors = [r for r in results if r.get("status") != "ok"]
    print(f"\n{'='*60}")
    print(f"Completed: {len(ok)}/{len(results)} | Errors: {len(errors)}")
    if ok:
        agg = _aggregate(ok)
        print(f"Average scores: relevance={agg['relevance']} completeness={agg['completeness']} "
              f"validity={agg['scientific_validity']} clarity={agg['clarity']} total={agg['total']}/20")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch evaluate SPARQ on Q_dataset.json")
    parser.add_argument("--grade-min", type=int, default=None, help="Only run questions with grade >= N")
    parser.add_argument("--questions", type=int, nargs="+", default=None, help="Specific question indices")
    args = parser.parse_args()

    asyncio.run(run_batch(grade_min=args.grade_min, indices=args.questions))
