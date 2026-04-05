from __future__ import annotations

from datetime import datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class RouterOutput(BaseModel):
    """Output of the router node."""
    route: Literal["analysis", "knowledge", "out_of_scope"] = Field(
        ...,
        description=(
            "'analysis' — requires data loading and statistical computation; "
            "'knowledge' — answerable from domain knowledge without data; "
            "'out_of_scope' — unrelated to food safety, public health, or socioeconomics"
        ),
    )
    direct_answer: Optional[str] = Field(
        None,
        description="A direct answer to the query — required when route is 'knowledge', null otherwise.",
    )


# ---------------------------------------------------------------------------
# Planner
# ---------------------------------------------------------------------------

class ResearchStep(BaseModel):
    """A single step in the research agenda."""
    description: str = Field(..., description="What to do in this step — be specific about method and data")
    rationale: str = Field(..., description="Why this step is necessary to answer the research question")
    datasets: List[str] = Field(..., description="Dataset names required for this step")
    expected_outputs: List[str] = Field(
        ...,
        description="What this step should produce (e.g., 'correlation matrix', 'bar chart of serotype counts')",
    )


class ResearchAgenda(BaseModel):
    """A structured research plan produced by the Planner."""
    question: str = Field(..., description="The research question, formalized and made precise")
    hypothesis: str = Field(..., description="A testable hypothesis to be evaluated by the analysis")
    approach: str = Field(
        ...,
        description="A narrative describing the overall analytical approach, methods, and logic",
    )
    steps: List[ResearchStep] = Field(..., description="Ordered research steps")
    expected_figures: List[str] = Field(
        default_factory=list,
        description="Descriptions of plots/tables expected from the full analysis",
    )
    notes: str = Field(
        "",
        description="Caveats, data quality concerns, or things the researcher should be aware of",
    )


# ---------------------------------------------------------------------------
# Researcher
# ---------------------------------------------------------------------------

class ResearcherOutput(BaseModel):
    """Structured findings from one research session."""
    summary: str = Field(..., description="Narrative of what was accomplished in this session")
    key_findings: List[str] = Field(
        ...,
        description="Specific, citable findings — each a single verifiable claim with numbers where applicable",
    )
    figures_generated: List[str] = Field(
        default_factory=list,
        description="Filenames of figures saved to the output directory",
    )
    data_notes: str = Field(
        "",
        description="Caveats about data quality, missing data, assumptions made, or analytical limitations",
    )


# ---------------------------------------------------------------------------
# Critic
# ---------------------------------------------------------------------------

class Critique(BaseModel):
    """Structured review of the researcher's output."""
    approved: bool = Field(
        ...,
        description="True if the research adequately addresses the agenda; False if revision is needed",
    )
    issues: List[str] = Field(
        default_factory=list,
        description="Specific problems that must be fixed (empty if approved)",
    )
    suggestions: List[str] = Field(
        default_factory=list,
        description="Optional improvement hints (non-blocking)",
    )


# ---------------------------------------------------------------------------
# Synthesizer
# ---------------------------------------------------------------------------

class Report(BaseModel):
    """A structured scientific report produced by the Synthesizer."""
    title: str = Field(..., description="A concise, descriptive title in academic style")
    abstract: str = Field(
        ...,
        description="A 100-150 word structured abstract: background, objective, methods, results, conclusion",
    )
    methods: str = Field(
        ...,
        description="Datasets used, preprocessing steps, statistical methods, and software/tools",
    )
    results: str = Field(
        ...,
        description="Key findings with specific numbers; reference figures as 'Figure N' where applicable",
    )
    discussion: str = Field(
        ...,
        description="Interpretation of results, comparison to prior knowledge, implications",
    )
    conclusion: str = Field(
        ...,
        description="Direct answer to the original question; key takeaway in 2-3 sentences",
    )
    limitations: str = Field(
        ...,
        description="Honest description of analytical limitations, data gaps, and what cannot be concluded",
    )


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

class Judgement(BaseModel):
    """LLM-as-judge evaluation of a Report against its originating question."""
    relevance: int = Field(..., ge=1, le=5, description="Does the report answer the question? (1=not at all, 5=fully)")
    completeness: int = Field(..., ge=1, le=5, description="Are all aspects of the question addressed?")
    scientific_validity: int = Field(..., ge=1, le=5, description="Are methods and claims statistically sound?")
    clarity: int = Field(..., ge=1, le=5, description="Is the report clearly written and well-organized?")
    rationale: str = Field(..., description="Reasoning for the scores — one paragraph")

    @property
    def total(self) -> int:
        return self.relevance + self.completeness + self.scientific_validity + self.clarity


# ---------------------------------------------------------------------------
# Run metadata (for ablation studies)
# ---------------------------------------------------------------------------

class NodeTiming(BaseModel):
    start: datetime
    end: datetime

    @property
    def duration_seconds(self) -> float:
        return (self.end - self.start).total_seconds()


class RunMetadata(BaseModel):
    """Timing and configuration metadata captured per run."""
    run_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    node_timings: dict[str, NodeTiming] = Field(default_factory=dict)
    revision_count: int = 0
    llm_config_snapshot: dict = Field(
        default_factory=dict,
        description="Snapshot of the llm_config used in this run (for ablation reproducibility)",
    )
