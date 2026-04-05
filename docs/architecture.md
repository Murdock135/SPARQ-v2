# SPARQ Architecture

## Graph

```
START
  │
  ▼
router  ─── "out_of_scope" ──────────────────────────────────────────────────┐
  │                                                                           │
  ├── "knowledge" ────────────────────────────────────────────────┐          │
  │                                                                │          │
  └── "analysis"                                                  │          │
        │                                                          │          │
        ▼                                                          │          │
      planner                                                      │          │
        │                                                          │          │
        ▼                                                          │          │
      researcher ◄─────────────────────────┐                      │          │
        │                                  │ (rejected            │          │
        ▼                                  │  revision_count < 2) │          │
      critic ─── "researcher" ─────────────┘                      │          │
        │                                                          │          │
        └── "synthesizer" ──────────────────────────────────────► │          │
                                                                   ▼          │
                                                              synthesizer     │
                                                                   │          │
                                                                   ▼          │
                                                                 saver ◄──────┘
                                                                   │
                                                                  END
```

## Node Responsibilities

| Node | File | Mechanism | Output |
|------|------|-----------|--------|
| **Router** | `nodes/router.py` | `with_structured_output` | `route`, `direct_answer` |
| **Planner** | `nodes/planner.py` | `with_structured_output` | `research_agenda`, `data_context` |
| **Researcher** | `nodes/researcher.py` | ReAct agent + tools | `research_log` append |
| **Critic** | `nodes/critic.py` | `with_structured_output` | `critique`, `revision_count` |
| **Synthesizer** | `nodes/synthesizer.py` | `with_structured_output` | `report` |
| **Saver** | `nodes/saver.py` | filesystem | writes to `run_dir` |

## Key Design Decisions

### Why ReAct only in Researcher?
Router, Planner, Critic, and Synthesizer make a single structured decision — they don't need to call tools or iterate. ReAct is only warranted where the agent needs to act, observe, and adapt: the Researcher.

### Why a Critic loop?
The Researcher can make errors: wrong statistical test, missed datasets, uncaptioned figures, hallucinated numbers. A separate Critic LLM reviewing the work and routing back for revision mimics peer review. Max 2 revisions prevent infinite loops.

### Why structured output everywhere?
All nodes except Researcher return Pydantic models. This enforces schema, gives the Synthesizer citable structured data (not a flat string), and makes the trace fully typed for downstream evaluation.

### Namespace scoping
The Python REPL namespace is scoped to `run_id` (via a tmpfile path passed before the run starts) so concurrent executions don't pollute each other.

### research_log accumulates
`research_log: Annotated[list[ResearcherOutput], operator.add]` grows on each revision. The Synthesizer uses the last entry; the full log is available for ablation analysis.

## Tools Available to Researcher

```
python_repl_tool         — persistent subprocess REPL with pickling
load_dataset             — load CSV/Excel by path + sheet
get_sheet_names          — inspect Excel workbooks
find_csv_excel_files     — discover files in a directory
get_cached_dataset_path  — resolve HuggingFace cache path
get_next_figure_number   — returns "Figure N" before saving a plot
interpret_plot           — multimodal LLM describes a saved image
write_file               — write a file to output_dir
read_file                — read a file from output_dir
list_directory           — list output_dir contents
```

## File Layout

```
src/sparq/
├── nodes/
│   ├── router.py
│   ├── planner.py
│   ├── researcher.py       ← new (replaces executor.py)
│   ├── critic.py           ← new
│   ├── synthesizer.py      ← new (replaces aggregator.py)
│   └── saver.py
├── schemas/
│   ├── state.py            ← new State with typed fields
│   ├── output_schemas.py   ← ResearchAgenda, ResearcherOutput, Critique, Report
│   └── data_context.py     ← unchanged
├── tools/
│   ├── python_repl/        ← unchanged
│   ├── data_discovery_tools.py  ← unchanged
│   ├── filesystemtools.py  ← unchanged
│   ├── vision_tools.py     ← new
│   └── figure_tools.py     ← new
├── eval/
│   ├── judge.py            ← LLM-as-judge scorer
│   ├── batch.py            ← batch runner over Q_dataset.json
│   └── ablation.py         ← ablation runner
├── prompts/
│   ├── router_message.txt
│   ├── planner_message.txt
│   ├── researcher_message.txt   ← new
│   ├── critic_message.txt       ← new
│   └── synthesizer_message.txt  ← new
├── system.py               ← rewritten
├── settings.py             ← extended (critic, synthesizer, vision nodes)
└── default_config.toml     ← extended
```

## Evaluation Harness

Located at `src/sparq/eval/`. Three components:

1. **judge.py** — LLM-as-judge: scores a `Report` on relevance, completeness, validity, clarity (1–5 each)
2. **batch.py** — runs SPARQ over all questions in `data/Q_dataset.json`, collects `Judgement` per question
3. **ablation.py** — runs same question under multiple config overrides, supports producing paper tables

All evaluation runs write to `output/eval/`.
