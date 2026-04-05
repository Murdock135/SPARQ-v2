"""
LLM-as-judge scorer.

Evaluates a SPARQ Report against the original question on four dimensions:
  - relevance        (1-5): does the report answer the question?
  - completeness     (1-5): are all aspects addressed?
  - scientific_validity (1-5): are methods and claims sound?
  - clarity          (1-5): is the report well-written and organised?

Usage:
    from sparq.eval.judge import judge_report
    from sparq.schemas.output_schemas import Report, Judgement

    judgement: Judgement = judge_report(
        question="Which serotypes are most prevalent in Missouri?",
        report=my_report,
        llm_config=settings.llm_config.judge,
    )
    print(judgement.total, judgement.rationale)
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage

from sparq.schemas.output_schemas import Judgement, Report
from sparq.settings import LLMSetting
from sparq.utils.get_llm import get_llm

_JUDGE_PROMPT = """\
You are an expert epidemiologist and scientific peer reviewer evaluating an automated analysis report.

Score the report on EXACTLY these four dimensions, each on a 1-5 integer scale:

**relevance** — Does the report directly answer the user's question?
  1 = completely misses the question
  3 = partially answers it
  5 = fully and precisely answers it

**completeness** — Are all aspects of the question addressed? Are expected analyses present?
  1 = major aspects missing
  3 = most aspects covered, minor gaps
  5 = comprehensive coverage

**scientific_validity** — Are statistical methods appropriate? Are claims supported by numbers?
Are there hallucinated statistics or unsupported conclusions?
  1 = significant errors or hallucinations
  3 = mostly sound with minor issues
  5 = rigorous, all claims traceable to data

**clarity** — Is the report clearly written, logically organised, and figures properly referenced?
  1 = hard to follow
  3 = clear but could be improved
  5 = publication-ready

Then write one paragraph of rationale explaining your scores, citing specific examples from the report.

Be strict. A score of 5 requires truly excellent work in that dimension.
"""


def judge_report(question: str, report: Report, llm_config: LLMSetting) -> Judgement:
    """Score a Report against the original question."""
    llm = get_llm(model=llm_config.model_name, provider=llm_config.provider)
    structured_llm = llm.with_structured_output(Judgement)

    report_text = (
        f"**Original Question:** {question}\n\n"
        f"**Title:** {report.title}\n\n"
        f"**Abstract:** {report.abstract}\n\n"
        f"**Methods:** {report.methods}\n\n"
        f"**Results:** {report.results}\n\n"
        f"**Discussion:** {report.discussion}\n\n"
        f"**Conclusion:** {report.conclusion}\n\n"
        f"**Limitations:** {report.limitations}"
    )

    judgement: Judgement = structured_llm.invoke([
        SystemMessage(content=_JUDGE_PROMPT),
        HumanMessage(content=report_text),
    ])
    return judgement
