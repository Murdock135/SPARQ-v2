from __future__ import annotations

import uuid
from datetime import datetime
from functools import partial
from pathlib import Path

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy
from rich import print
import pydantic_core

from sparq.nodes.critic import critic_node, critic_route
from sparq.nodes.planner import planner_node
from sparq.nodes.researcher import researcher_node
from sparq.nodes.router import router_func, router_node
from sparq.nodes.synthesizer import synthesizer_node
from sparq.nodes.saver import saver_node
from sparq.schemas.output_schemas import RunMetadata
from sparq.schemas.state import State
from sparq.settings import AgenticSystemSettings
from sparq.utils.get_package_dir import get_package_dir
from sparq.utils.helpers import load_text


class AgenticSystem:
    def __init__(self):
        self.settings = AgenticSystemSettings()
        prompts_dir = self.settings.paths.prompts_dir
        if not prompts_dir.is_absolute():
            prompts_dir = get_package_dir() / prompts_dir
        self.prompts = {
            "router":      load_text(prompts_dir / "router_message.txt"),
            "planner":     load_text(prompts_dir / "planner_message.txt"),
            "researcher":  load_text(prompts_dir / "researcher_message.txt"),
            "critic":      load_text(prompts_dir / "critic_message.txt"),
            "synthesizer": load_text(prompts_dir / "synthesizer_message.txt"),
        }

    def _build_graph(self, run_dir: Path):
        cfg = self.settings.llm_config

        _router      = partial(router_node,      llm_config=cfg.router,      prompt=self.prompts["router"])
        _planner     = partial(planner_node,      llm_config=cfg.planner,     sys_prompt=self.prompts["planner"])
        _researcher  = partial(researcher_node,   llm_config=cfg.researcher,  prompt=self.prompts["researcher"],  output_dir=run_dir / "researcher")
        _critic      = partial(critic_node,       llm_config=cfg.critic,      prompt=self.prompts["critic"])
        _synthesizer = partial(synthesizer_node,  llm_config=cfg.synthesizer, prompt=self.prompts["synthesizer"], output_dir=run_dir / "researcher")
        _saver       = partial(saver_node,        save_dir=run_dir)

        g = StateGraph(state_schema=State)

        g.add_node("router",      _router)
        g.add_node(
            "planner",
            _planner,
            retry=RetryPolicy(
                max_attempts=5,
                retry_on=pydantic_core._pydantic_core.ValidationError,
            ),
        )
        g.add_node("researcher",  _researcher)
        g.add_node("critic",      _critic)
        g.add_node("synthesizer", _synthesizer)
        g.add_node("saver",       _saver)

        g.add_edge(START, "router")

        # Router branches:
        #   analysis     → planner → researcher → critic (loop) → synthesizer → saver
        #   knowledge    → synthesizer → saver  (no data work needed)
        #   out_of_scope → saver  (save what we have and exit)
        g.add_conditional_edges(
            "router",
            router_func,
            {
                "analysis":     "planner",
                "knowledge":    "synthesizer",
                "out_of_scope": "saver",
            },
        )

        g.add_edge("planner",    "researcher")
        g.add_edge("researcher", "critic")
        g.add_conditional_edges(
            "critic",
            critic_route,
            {
                "researcher":  "researcher",
                "synthesizer": "synthesizer",
            },
        )
        g.add_edge("synthesizer", "saver")
        g.add_edge("saver",       END)

        return g.compile()

    async def run(self, user_query: str):
        run_id = str(uuid.uuid4())[:8]
        run_dir: Path = self.settings.paths.run_dir
        run_dir.mkdir(parents=True, exist_ok=True)

        run_metadata = RunMetadata(
            run_id=run_id,
            start_time=datetime.now(),
            llm_config_snapshot=self.settings.llm_config.model_dump(),
        )

        initial_state: dict = {
            "query": user_query,
            "route": None,
            "direct_answer": None,
            "research_agenda": None,
            "data_context": None,
            "research_log": [],
            "critique": None,
            "revision_count": 0,
            "report": None,
            "run_id": run_id,
            "run_metadata": run_metadata,
        }

        graph = self._build_graph(run_dir)

        async for chunk in graph.astream(input=initial_state, stream_mode="updates"):
            print(chunk)


# Keep old name as alias for backwards compatibility with scripts
Agentic_system = AgenticSystem
