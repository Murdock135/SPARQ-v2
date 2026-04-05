# SPARQ v2 — Implementation TODO

## Phase 1 — Schemas (foundation everything else depends on)
- [x] `schemas/output_schemas.py` — ResearchAgenda, ResearchStep, ResearcherOutput, Critique, Report, RunMetadata
- [x] `schemas/state.py` — new State with typed fields + reducers

## Phase 2 — Tools
- [x] `tools/vision_tools.py` — interpret_plot
- [x] `tools/figure_tools.py` — get_next_figure_number
- [x] `tools/python_repl/namespace.py` — add set_persistent_ns_path() for run-scoped namespaces

## Phase 3 — Nodes
- [x] `nodes/router.py` — structured output (no ReAct)
- [x] `nodes/planner.py` — ResearchAgenda output (no ReAct)
- [x] `nodes/researcher.py` — ReAct agent with all tools + vision + figure numbering
- [x] `nodes/critic.py` — structured LLM review
- [x] `nodes/synthesizer.py` — structured Report output
- [x] `nodes/saver.py` — writes trace.json, report.md, metadata.json, best-effort PDF

## Phase 4 — System + Config
- [x] `system.py` — new graph with critic loop
- [x] `settings.py` — add critic, synthesizer, vision to LLMSettings
- [x] `default_config.toml` — add all new node config sections

## Phase 5 — Prompts
- [x] `prompts/router_message.txt`
- [x] `prompts/planner_message.txt`
- [x] `prompts/researcher_message.txt`
- [x] `prompts/critic_message.txt`
- [x] `prompts/synthesizer_message.txt`

## Phase 6 — Evaluation Harness
- [ ] `eval/__init__.py`
- [ ] `eval/judge.py` — LLM-as-judge scorer
- [ ] `eval/batch.py` — batch runner over Q_dataset.json
- [ ] `eval/ablation.py` — ablation config runner

## Phase 7 — Cleanup
- [x] Delete `nodes/aggregator.py`
- [x] Delete `nodes/formatter.py`
- [x] Delete `settings_old.py`
- [x] Delete `prompts/analyzer_message.txt`, `prompts/explorer_message.txt`, `prompts/explorer_user_message.txt`

## Phase 8 — Testing
- [ ] Update `tests/` for new schemas
- [ ] Add smoke test for full graph run (mocked LLMs)
- [ ] Validate eval harness on a single question

## Paper-specific
- [ ] Run full eval on Q_dataset.json, collect baseline scores
- [ ] Ablation: with/without critic loop
- [ ] Ablation: with/without plot interpretation
- [ ] Ablation: planner model size (flash vs pro)
