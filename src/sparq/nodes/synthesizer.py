"""
Synthesizer node — produces a structured scientific report.

Takes the full research context (agenda, all researcher outputs, figures on disk)
and produces a typed Report. Unlike the old aggregator (which returned a plain
string), the Report is a Pydantic model with distinct sections, making it
straightforward to render as markdown, evaluate with LLM-as-judge, or pass to
downstream paper-writing tools.

For knowledge-route queries (no data analysis), the synthesizer formats the
router's direct_answer into a minimal report.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import PromptTemplate

from sparq.schemas.output_schemas import Report, ResearchAgenda, ResearcherOutput
from sparq.schemas.state import State
from sparq.settings import LLMSetting
from sparq.utils.get_llm import get_llm

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".svg"}


def _build_figure_manifest(output_dir: Path) -> str:
    """Build an ordered figure manifest from files on disk."""
    if not output_dir.exists():
        return "No figures generated."
    images = sorted(
        (f for f in output_dir.iterdir() if f.suffix.lower() in _IMAGE_SUFFIXES),
        key=lambda f: f.stat().st_mtime,
    )
    if not images:
        return "No figures generated."
    lines = ["Figures available (in creation order):"]
    for i, img in enumerate(images, start=1):
        lines.append(f"  Figure {i}: {img.name}")
    return "\n".join(lines)


def synthesizer_node(
    state: State,
    llm_config: LLMSetting,
    prompt: str,
    output_dir: Path,
) -> dict:
    """
    Produce a structured Report from the research findings.

    Handles both the 'analysis' route (uses research_log) and the 'knowledge'
    route (formats direct_answer into a minimal report).
    """
    route = state.get("route")
    llm = get_llm(model=llm_config.model_name, provider=llm_config.provider)
    structured_llm = llm.with_structured_output(Report)

    # --- Knowledge route: no data analysis was done ---
    if route == "knowledge":
        direct_answer = state.get("direct_answer") or ""
        content = (
            f"Original question: {state['query']}\n\n"
            f"Answer from domain knowledge:\n{direct_answer}\n\n"
            f"Format this into a concise scientific report. There are no figures or "
            f"statistical analyses — reflect that honestly in the methods and limitations sections."
        )
        report: Report = structured_llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=content),
        ])
        return {"report": report}

    # --- Analysis route: use research findings ---
    agenda: ResearchAgenda = state.get("research_agenda")
    research_log: list[ResearcherOutput] = state.get("research_log", [])
    figure_manifest = _build_figure_manifest(output_dir)

    # Compile all findings (may be multiple if revisions happened)
    findings_text = ""
    for i, entry in enumerate(research_log, start=1):
        label = f"Research Session {i}" if len(research_log) > 1 else "Research Findings"
        findings_text += (
            f"\n\n=== {label} ===\n"
            f"Summary: {entry.summary}\n\n"
            f"Key Findings:\n" + "\n".join(f"  - {f}" for f in entry.key_findings)
            + f"\n\nData Notes: {entry.data_notes}"
        )

    system_prompt_str: str = (
        PromptTemplate.from_template(prompt)
        .partial(figure_manifest=figure_manifest)
        .invoke(input={})
        .to_string()
    )

    content = (
        f"Original question: {state['query']}\n\n"
        f"Research Question (formalized): {agenda.question if agenda else state['query']}\n"
        f"Hypothesis: {agenda.hypothesis if agenda else 'N/A'}\n"
        f"Approach: {agenda.approach if agenda else 'N/A'}\n"
        + findings_text
        + f"\n\n{figure_manifest}"
    )

    report = structured_llm.invoke([
        SystemMessage(content=system_prompt_str),
        HumanMessage(content=content),
    ])

    return {"report": report}
