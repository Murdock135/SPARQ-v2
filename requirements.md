# SPARQ v2 — System Requirements

## Purpose

SPARQ is an autonomous data science agent for pathogeno-socio-economic analysis.
Its primary use case is Salmonella epidemiology: answering structured and open-ended
research questions over curated datasets (PulseNet, SVI, FSIS, climate, food insecurity, etc.).

The system must produce output of sufficient quality to support an academic paper:
*"A Multi-Agent System Is All You Need for Pathogeno-Socio-Economic Analysis."*
This means reproducible traces, ablation-ready configuration, and scientifically valid reports.

---

## Graph Architecture

```
START → router
  "analysis"    → planner → researcher → critic ─┬─(approved / max revisions)→ synthesizer → saver → END
  "knowledge"   → synthesizer → saver → END       └─(rejected, revision < 2)──→ researcher (retry)
  "out_of_scope"→ saver → END
```

---

## Node Specifications

### Router
- **Input**: raw user query
- **Output**: `route: Literal["analysis", "knowledge", "out_of_scope"]`, `answer: str | None`
- **Mechanism**: single structured LLM call (`with_structured_output`)
- **No ReAct** — there are no tools to invoke

### Planner
- **Input**: query + data manifest + dataset summaries
- **Output**: `ResearchAgenda` — a full research plan (not a flat step list):
  - `question`: formalized research question
  - `hypothesis`: testable hypothesis
  - `approach`: analytical narrative
  - `steps`: ordered list of `ResearchStep` (description, rationale, datasets, expected_outputs)
  - `expected_figures`: what plots/tables should be produced
  - `notes`: caveats, data quality notes
- **Mechanism**: single structured LLM call

### Researcher
- **Input**: `ResearchAgenda`, `data_context`, `output_dir`, optional `critique` (for revision)
- **Output**: `ResearcherOutput` — structured findings from one research session:
  - `summary`: narrative of what was done
  - `key_findings`: list of specific, citable findings
  - `figures_generated`: list of figure filenames
  - `data_notes`: caveats, limitations, anomalies
- **Mechanism**: ReAct agent (the only node that justifies it — has real tools)
- **Tools**:
  - `python_repl_tool` — execute Python in a persistent subprocess REPL
  - `load_dataset` — load a dataset by path/sheet
  - `get_sheet_names`, `find_csv_excel_files`, `get_cached_dataset_path` — data discovery
  - `get_next_figure_number(directory)` — returns "Figure N" label before saving any plot
  - `interpret_plot(file_path)` — calls a multimodal LLM to describe a saved figure
  - Filesystem tools (read, write, list) for managing output
- **Namespace**: scoped to `run_id` so concurrent runs don't collide
- **On revision**: receives the critic's issues and must address them explicitly

### Critic
- **Input**: `ResearchAgenda`, latest `ResearcherOutput`
- **Output**: `Critique`:
  - `approved: bool`
  - `issues: list[str]` — specific problems (empty if approved)
  - `suggestions: list[str]` — optional improvement hints
- **Mechanism**: single structured LLM call
- **Routing**: if not approved AND `revision_count < 2` → back to Researcher; else → Synthesizer
- **Always approves on second review** to prevent infinite loops

### Synthesizer
- **Input**: query, `ResearchAgenda`, `research_log` (list of `ResearcherOutput`), figure manifest
- **Output**: `Report`:
  - `title`: paper-style title
  - `abstract`: 150-word structured abstract
  - `methods`: what data and methods were used
  - `results`: findings with figure references ("as shown in Figure 1")
  - `discussion`: interpretation, comparison to literature
  - `conclusion`: answer to the original question
  - `limitations`: honest caveats
- **Mechanism**: single structured LLM call
- **Figure awareness**: synthesizer receives a manifest mapping filename → figure number → description

### Saver
- **Input**: full state, `save_dir`
- **Writes**:
  - `trace.json` — full state dump for reproducibility
  - `report.md` — markdown rendering of `Report`
  - `metadata.json` — run timings and model config
- **PDF**: best-effort pandoc conversion of `report.md` → `report.pdf`

---

## Schema Definitions

### State (TypedDict)
```python
query: str
route: Literal["analysis", "knowledge", "out_of_scope"] | None
direct_answer: str | None           # for "knowledge" route

research_agenda: ResearchAgenda | None
data_context: DataContext | None

research_log: Annotated[list[ResearcherOutput], operator.add]  # accumulates across revisions
critique: Critique | None
revision_count: int

report: Report | None

run_id: str
run_metadata: RunMetadata
```

### Key Output Schemas
See `src/sparq/schemas/output_schemas.py`.

---

## Tool Specifications

### `get_next_figure_number(directory: str) -> str`
- Counts `.png`, `.jpg`, `.jpeg`, `.svg` files in `directory`
- Returns `"Figure {count + 1}"`
- Must be called before saving any plot; the returned label goes in the plot title

### `interpret_plot(file_path: str) -> str`
- Reads and base64-encodes the image at `file_path`
- Calls a configured multimodal LLM with the image + instruction to describe findings
- Returns a text description of the figure's key message
- Uses a separate `vision` LLM config (must be a multimodal model)

---

## Configuration

All LLM choices are configurable per-node in `config.toml`:
```toml
[llm_config.router]
[llm_config.planner]
[llm_config.researcher]
[llm_config.critic]
[llm_config.synthesizer]
[llm_config.vision]      # must be multimodal
```

---

## Evaluation Harness

Located at `src/sparq/eval/`. Supports:

1. **LLM-as-judge scoring** (`eval/judge.py`):
   - Runs a `Report` through a judge LLM against the original question
   - Scores: relevance (1-5), completeness (1-5), scientific validity (1-5), clarity (1-5)
   - Returns `Judgement` with scores + rationale per dimension

2. **Batch evaluation** (`eval/batch.py`):
   - Reads `data/Q_dataset.json`
   - Runs SPARQ on each question
   - Aggregates scores; outputs `eval_results.json`

3. **Ablation runner** (`eval/ablation.py`):
   - Accepts a config override dict
   - Runs the same question under N configurations
   - Used to produce ablation tables in the paper

---

## What Is Kept from v1

| Component | Decision | Reason |
|-----------|----------|--------|
| `tools/python_repl/` | Kept unchanged | Production-quality; subprocess isolation, pickling, AST eval all work |
| `tools/data_discovery_tools.py` | Kept | Good tool set |
| `tools/filesystemtools.py` | Kept | Good tool set |
| `utils/` | Kept | Solid utility functions |
| `settings.py` | Kept + extended | Well-designed, just needs new node keys |
| `schemas/data_context.py` | Kept | Unchanged |
| `data/` | Kept | Datasets |

## What Is Replaced

| Old | New | Why |
|-----|-----|-----|
| `nodes/executor.py` | `nodes/researcher.py` | True ReAct, self-directing, vision-capable |
| `nodes/aggregator.py` | `nodes/synthesizer.py` | Structured scientific report |
| `nodes/formatter.py` | — | Was empty stub |
| Flat `Plan` + `Step` | `ResearchAgenda` + `ResearchStep` | Research framing, not just task list |
| `executor_results: dict` | `research_log: list[ResearcherOutput]` | Typed, accumulates across revisions |
| `system.py` | Rewritten | New graph with critic loop |

---

## Non-Goals

- Web search / literature retrieval (future)
- Vision input from user (future)
- Real-time streaming UI (future)
- Multi-user session management (future)
