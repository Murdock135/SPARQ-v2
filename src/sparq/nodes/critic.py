"""
Critic node — independent peer review of the researcher's output.

A single structured LLM call that evaluates whether the ResearcherOutput
adequately addresses the ResearchAgenda. If not (and revision_count < 2),
the graph routes back to the researcher.

Max 2 revisions are enforced by the routing function — the critic itself
just evaluates honestly; the loop cap is in system.py.
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from sparq.schemas.output_schemas import Critique, ResearchAgenda, ResearcherOutput
from sparq.schemas.state import State
from sparq.settings import LLMSetting
from sparq.utils.get_llm import get_llm


def critic_node(state: State, llm_config: LLMSetting, prompt: str) -> dict:
    """
    Review the latest researcher output against the research agenda.

    Returns a partial state update with the Critique.
    """
    agenda: ResearchAgenda = state["research_agenda"]
    research_log: list[ResearcherOutput] = state.get("research_log", [])
    latest: ResearcherOutput = research_log[-1]

    llm = get_llm(model=llm_config.model_name, provider=llm_config.provider)
    structured_llm = llm.with_structured_output(Critique)

    review_content = (
        f"=== RESEARCH AGENDA ===\n"
        f"Question: {agenda.question}\n"
        f"Hypothesis: {agenda.hypothesis}\n"
        f"Approach: {agenda.approach}\n"
        f"Steps:\n"
        + "\n".join(
            f"  {i+1}. {step.description} → expects: {', '.join(step.expected_outputs)}"
            for i, step in enumerate(agenda.steps)
        )
        + f"\n\n=== RESEARCHER OUTPUT ===\n"
        f"Summary: {latest.summary}\n\n"
        f"Key Findings:\n"
        + "\n".join(f"  - {f}" for f in latest.key_findings)
        + f"\n\nFigures generated: {', '.join(latest.figures_generated) or 'none'}"
        + f"\n\nData notes: {latest.data_notes}"
    )

    critique: Critique = structured_llm.invoke([
        SystemMessage(content=prompt),
        HumanMessage(content=review_content),
    ])

    return {"critique": critique}


def critic_route(state: State) -> str:
    """Routing function called after critic_node.

    Routes back to researcher if:
      - The critique was not approved, AND
      - revision_count < 2 (cap at two revision rounds)

    Otherwise routes to synthesizer.
    """
    critique: Critique | None = state.get("critique")
    revision_count: int = state.get("revision_count", 0)

    if critique is not None and not critique.approved and revision_count < 2:
        return "researcher"
    return "synthesizer"
