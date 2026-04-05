"""
Researcher node — the core analytical engine.

A ReAct agent that receives the full ResearchAgenda and works through it
autonomously. Unlike the old executor (which iterated steps externally in
Python), the researcher decides what to do next, calls tools, sees its own
outputs (including plots via interpret_plot), and produces a ResearcherOutput
when satisfied.

On revision runs the agent receives the critic's issues as additional context
so it can address specific problems.
"""

from __future__ import annotations

import pickle
from pathlib import Path

from langchain_core.messages import SystemMessage
from langchain_core.prompts import PromptTemplate
from langgraph.prebuilt import create_react_agent

from sparq.schemas.output_schemas import Critique, ResearchAgenda, ResearcherOutput
from sparq.schemas.state import State
from sparq.settings import LLMSetting
from sparq.tools.data_discovery_tools import (
    find_csv_excel_files,
    get_cached_dataset_path,
    get_sheet_names,
    load_dataset,
)
from sparq.tools.figure_tools import get_next_figure_number
from sparq.tools.filesystemtools import filesystemtools
from sparq.tools.python_repl.namespace import set_persistent_ns_path
from sparq.tools.python_repl.python_repl_tool import python_repl_tool
from sparq.tools.vision_tools import interpret_plot
from sparq.utils.get_llm import get_llm


def _init_namespace(ns_path: Path) -> None:
    """Create an empty pickle namespace file at the given path."""
    ns_path.parent.mkdir(parents=True, exist_ok=True)
    if not ns_path.exists():
        with open(ns_path, "wb") as f:
            pickle.dump({}, f)
    set_persistent_ns_path(str(ns_path))


def _format_critique_context(critique: Critique | None) -> str:
    if critique is None or critique.approved:
        return ""
    lines = ["\n\n--- REVISION REQUEST ---"]
    lines.append("Your previous analysis was reviewed. The following issues must be addressed:\n")
    for issue in critique.issues:
        lines.append(f"  - {issue}")
    if critique.suggestions:
        lines.append("\nSuggestions (non-blocking):")
        for s in critique.suggestions:
            lines.append(f"  - {s}")
    lines.append("\nPlease re-run your analysis addressing all listed issues.")
    return "\n".join(lines)


def researcher_node(
    state: State,
    llm_config: LLMSetting,
    prompt: str,
    output_dir: Path,
) -> dict:
    """
    Execute the research agenda autonomously using a ReAct agent.

    Returns a partial state update: appends one ResearcherOutput to research_log
    and increments revision_count.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    # Scope namespace to this run so concurrent runs don't collide
    ns_path = output_dir / "namespace.pkl"
    _init_namespace(ns_path)

    agenda: ResearchAgenda = state["research_agenda"]
    data_context = state["data_context"]
    critique: Critique | None = state.get("critique")

    llm = get_llm(model=llm_config.model_name, provider=llm_config.provider)

    tools = [
        python_repl_tool,
        load_dataset,
        get_sheet_names,
        find_csv_excel_files,
        get_cached_dataset_path,
        get_next_figure_number,
        interpret_plot,
    ] + filesystemtools(working_dir=str(output_dir), selected_tools="all")

    system_prompt_str: str = (
        PromptTemplate.from_template(prompt)
        .partial(
            data_context=str(data_context),
            output_dir=str(output_dir),
        )
        .invoke(input={})
        .to_string()
    )
    system_prompt = SystemMessage(content=system_prompt_str)

    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=system_prompt,
        response_format=(prompt, ResearcherOutput),
    )

    # Build user message: full agenda + any revision feedback
    agenda_text = (
        f"Research Question: {agenda.question}\n\n"
        f"Hypothesis: {agenda.hypothesis}\n\n"
        f"Approach: {agenda.approach}\n\n"
        f"Steps:\n"
        + "\n".join(
            f"  {i+1}. {step.description}\n"
            f"     Datasets: {', '.join(step.datasets) or 'any'}\n"
            f"     Expected outputs: {', '.join(step.expected_outputs)}"
            for i, step in enumerate(agenda.steps)
        )
        + f"\n\nExpected figures: {', '.join(agenda.expected_figures) or 'as needed'}"
        + f"\n\nNotes: {agenda.notes}"
        + _format_critique_context(critique)
    )

    agent_input = {"messages": [{"role": "user", "content": agenda_text}]}
    response = agent.invoke(
        agent_input,
        config={"recursion_limit": llm_config.recursion_limit},
    )

    findings: ResearcherOutput = response["structured_response"]

    return {
        "research_log": [findings],
        "revision_count": state.get("revision_count", 0) + 1,
    }
