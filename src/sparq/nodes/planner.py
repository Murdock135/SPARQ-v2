from sparq.schemas.state import State
from sparq.schemas.output_schemas import ResearchAgenda
from sparq.schemas.data_context import DataContext, load_data_context
from sparq.settings import (
    AgenticSystemSettings,
    ENVSettings,
    DATA_MANIFEST_PATH,
    DATA_SUMMARIES_SHORT_PATH,
    LLMSetting,
)
from sparq.utils.get_llm import get_llm

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import BasePromptTemplate, PromptTemplate


def planner_node(state: State, llm_config: LLMSetting, sys_prompt: str) -> dict:
    """
    Produce a ResearchAgenda from the user query and available data context.

    Returns a partial state update with research_agenda and data_context.
    """
    print("Making a research plan...")

    llm = get_llm(model=llm_config.model_name, provider=llm_config.provider)
    data_context = load_data_context(DATA_MANIFEST_PATH, DATA_SUMMARIES_SHORT_PATH)

    system_prompt_template: BasePromptTemplate = PromptTemplate.from_template(sys_prompt).partial(
        data_context=str(data_context),
    )
    _system_prompt: str = system_prompt_template.invoke(input={}).to_string()

    structured_llm = llm.with_structured_output(ResearchAgenda)
    agenda: ResearchAgenda = structured_llm.invoke([
        SystemMessage(content=_system_prompt),
        HumanMessage(content=state["query"]),
    ])

    print("Research agenda created.")
    return {"research_agenda": agenda, "data_context": data_context}


def test_planner():
    print("Running test code for planner.py")
    _ = ENVSettings()
    llm_config = AgenticSystemSettings().llm_config
    system_prompt = "Create a research plan to answer the user query.\n\nData context:\n{data_context}"
    user_query = "Is there a correlation between average temperature and Salmonella rates across U.S. climatic regions?"
    state = {"query": user_query}

    response = planner_node(state=state, llm_config=llm_config.planner, sys_prompt=system_prompt)
    agenda = response["research_agenda"]
    print(f"\nQuestion: {agenda.question}")
    print(f"Hypothesis: {agenda.hypothesis}")
    print(f"Steps ({len(agenda.steps)}):")
    for i, step in enumerate(agenda.steps, 1):
        print(f"  {i}. {step.description}")


if __name__ == "__main__":
    test_planner()
