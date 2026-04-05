from __future__ import annotations

import operator
from typing import Annotated, Literal, Optional, TypedDict

from sparq.schemas.output_schemas import (
    Critique,
    Report,
    ResearchAgenda,
    ResearcherOutput,
    RunMetadata,
)
from sparq.schemas.data_context import DataContext


class State(TypedDict):
    # ---- Input ----
    query: str

    # ---- Router output ----
    route: Optional[Literal["analysis", "knowledge", "out_of_scope"]]
    direct_answer: Optional[str]  # set when route == "knowledge"

    # ---- Planner output ----
    research_agenda: Optional[ResearchAgenda]
    data_context: Optional[DataContext]

    # ---- Researcher output ----
    # Annotated with operator.add so successive researcher runs (revisions) append
    # rather than replace — preserves full revision history for ablation analysis.
    research_log: Annotated[list[ResearcherOutput], operator.add]

    # ---- Critic output ----
    critique: Optional[Critique]
    revision_count: int  # number of times researcher has been invoked

    # ---- Synthesizer output ----
    report: Optional[Report]

    # ---- Run metadata ----
    run_id: str
    run_metadata: RunMetadata
