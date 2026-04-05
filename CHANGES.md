# CHANGES — v1 → v2

This file tracks the architectural and functional differences between the original
SPARQ pipeline (v1) and the redesigned system (v2).

---

## Graph Structure

| Aspect | v1 | v2 |
|--------|----|----|
| Route options | `True` (analysis) / `False` (direct) | `"analysis"` / `"knowledge"` / `"out_of_scope"` |
| Analysis path | `router → planner → executor → aggregator → saver` | `router → planner → researcher → critic → synthesizer → saver` |
| Knowledge path | `router → END` (nothing saved) | `router → synthesizer → saver` |
| Out-of-scope path | — | `router → saver` |
| Revision loop | None | `critic → researcher` (max 2 rounds) |

---

## Nodes

### Router
| Aspect | v1 | v2 |
|--------|----|-----|
| Mechanism | `create_react_agent(tools=[])` — ReAct with no tools; made 2 LLM calls (stream + invoke) | `llm.with_structured_output(Router)` — single structured call |
| Output schema | `route: bool`, `answer: str \| None` | `route: Literal["analysis","knowledge","out_of_scope"]`, `direct_answer: str \| None` |
| Direct answer handling | Routed to END — answer never saved | Routed to synthesizer then saver |

### Planner
| Aspect | v1 | v2 |
|--------|----|-----|
| Mechanism | `create_react_agent(tools=[])` — ReAct with no tools; made 2 LLM calls (stream + invoke) | `llm.with_structured_output(Plan)` — single structured call |
| Output schema | `Plan` (flat list of `Step` objects with step_description, datasets, rationale, task_type) | `ResearchAgenda` (question, hypothesis, approach, ordered `ResearchStep` list with expected_outputs, expected_figures, notes) |
| Planning depth | Task list | Research framing: formalizes question, states hypothesis, specifies expected outputs per step |

### Executor → Researcher
| Aspect | v1 | v2 |
|--------|----|----|
| Name | `executor_node` | `researcher_node` |
| Invocation | External Python loop: one `agent.invoke()` call per plan step | Single `agent.invoke()` with full agenda; agent self-directs |
| State mutation | `state['executor_results'] = results` inside loop (wrong), `return state` (wrong) | `return {'research_log': [findings], 'revision_count': count + 1}` |
| Tools | REPL, load_dataset, filesystem | Same + `get_next_figure_number`, `interpret_plot` |
| Namespace | Module-level global (`_PERSISTENT_NS_PATH`) — concurrent runs collide | Scoped to `run_dir / "namespace.pkl"` via `set_persistent_ns_path()` |
| Output schema | `ExecutorOutput` (execution_results: str, files_generated, misc) | `ResearcherOutput` (summary, key_findings: list, figures_generated, data_notes) |
| Vision | None | `interpret_plot` tool — agent calls multimodal LLM to describe saved figures |
| Figure numbering | None — no labeling | `get_next_figure_number` tool — agent labels figures sequentially |
| Revision support | None | Receives `Critique.issues` in prompt when on a revision pass |

### Aggregator → Synthesizer
| Aspect | v1 | v2 |
|--------|----|----|
| Name | `aggregator_node` | `synthesizer_node` |
| Mechanism | `llm.invoke(prompt_str)` — unstructured string | `llm.with_structured_output(Report)` — typed Pydantic model |
| Output | `answer: str` — plain text | `Report` (title, abstract, methods, results, discussion, conclusion, limitations) |
| Figure awareness | None | Receives figure manifest (filename → Figure N) built from files on disk |
| Route awareness | Not route-aware (crashes on missing `executor_results`) | Handles `"knowledge"` route with different prompt path |

### Critic (New)
| Aspect | v1 | v2 |
|--------|----|----|
| Existence | — | New node |
| Role | — | Structured peer review: checks completeness, statistical validity, figure coverage |
| Output | — | `Critique(approved, issues, suggestions)` |
| Effect | — | Routes back to researcher if not approved and revision_count < 2 |

### Saver
| Aspect | v1 | v2 |
|--------|----|----|
| Bug | `__obj` (NameError) in pydantic_encoder | Fixed to `obj` |
| Files written | `trace.json`, `final_answer.json` | `trace.json`, `report.md`, `metadata.json`, `report.pdf` (best-effort) |
| Markdown report | None | Full markdown rendering of structured `Report` |
| PDF | None | Best-effort `pandoc` conversion |
| Run metadata | None | Writes `metadata.json` with timings and LLM config snapshot |

---

## Schemas

### State
| Field | v1 | v2 |
|-------|----|-----|
| `route` | `bool \| None` | `Literal["analysis","knowledge","out_of_scope"] \| None` |
| `answer` | `str \| None` | Removed; replaced by `direct_answer` + `Report.conclusion` |
| `plan` | `Plan \| None` | `research_agenda: ResearchAgenda \| None` |
| `executor_results` | `dict` (untyped) | `research_log: Annotated[list[ResearcherOutput], operator.add]` (typed, accumulates) |
| `critique` | — | `Critique \| None` (new) |
| `revision_count` | — | `int` (new) |
| `report` | — | `Report \| None` (new) |
| `run_id` | — | `str` (new) |
| `run_metadata` | — | `RunMetadata` (new) |
| Type | `TypedDict` (no validation) | `TypedDict` with `Annotated` reducer on `research_log` |

---

## Tools

| Tool | v1 | v2 |
|------|----|-----|
| `get_next_figure_number` | — | New — returns `"Figure N"` label for sequential plot titling |
| `interpret_plot` | — | New — calls multimodal vision LLM to describe a saved figure |
| `python_repl_tool` | Global namespace (`_PERSISTENT_NS_PATH` module-level) | `set_persistent_ns_path()` added to scope namespace per run |

---

## Configuration

| Key | v1 | v2 |
|-----|----|-----|
| `llm_config.executor` | ✓ | Kept as legacy alias |
| `llm_config.aggregator` | ✓ | Kept as legacy alias |
| `llm_config.researcher` | — | New |
| `llm_config.critic` | — | New |
| `llm_config.synthesizer` | — | New |
| `llm_config.vision` | — | New — must be multimodal model |

---

## New Capabilities

1. **Critic loop** — independent peer review with up to 2 revision rounds
2. **Vision feedback** — researcher can interpret its own plots mid-analysis
3. **Figure numbering** — sequential labels enable synthesizer to reference figures
4. **Structured scientific report** — `Report` Pydantic model with distinct sections
5. **Run metadata** — timings and config snapshot per run for ablation studies
6. **Evaluation harness** — `eval/judge.py`, `eval/batch.py`, `eval/ablation.py`
7. **Concurrent run safety** — namespace scoped to run_id
8. **Data manifests tracked** — `src/sparq/data/` added to git via `.gitignore` exceptions

---

## Bug Fixes (from v1)

| Bug | Location | Fix |
|-----|----------|-----|
| Double LLM call | `router.py`, `planner.py` | Removed `agent.stream()` + `agent.invoke()` pattern; replaced with single structured call |
| ReAct without tools | `router.py`, `planner.py` | Replaced `create_react_agent(tools=[])` with `with_structured_output` |
| Executor state mutation inside loop | `executor.py:105` | Moved outside loop; return partial state only |
| Full state return from executor | `executor.py:107` | Changed to `return {'executor_results': results}` |
| `__obj` NameError in saver | `saver.py:12` | Fixed to `obj` |
| Direct answer never saved | `system.py:67` | Routed `False` → `"saver"` (then redesigned as `"knowledge"` → synthesizer → saver) |
| Global REPL namespace | `namespace.py` | Added `set_persistent_ns_path()` for run-scoped isolation |
