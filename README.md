# SPARQ

**Autonomous multi-agent data science for pathogeno-socio-economic analysis.**

SPARQ answers research questions over curated epidemiology datasets (PulseNet, NORS, SVI, Map the Meal Gap, Census) using a LangGraph pipeline of specialized LLM agents. It produces structured scientific reports suitable for academic publication.

---

## Architecture

```
router → planner → researcher → critic ─┬→ synthesizer → saver
                       ↑                └→ researcher  (revision, max 2×)

"knowledge" queries:   router → synthesizer → saver
"out of scope":        router → saver
```

| Node | Role |
|------|------|
| **Router** | Classifies query: `analysis`, `knowledge`, or `out_of_scope` |
| **Planner** | Produces a `ResearchAgenda` (formalized question, hypothesis, ordered steps) |
| **Researcher** | ReAct agent that runs Python code, loads data, generates figures, interprets plots |
| **Critic** | Peer-reviews the researcher's output; routes back for revision if needed |
| **Synthesizer** | Produces a structured `Report` (abstract, methods, results, discussion, conclusion, limitations) |
| **Saver** | Writes `trace.json`, `report.md`, `metadata.json`, and a best-effort `report.pdf` |

---

## Prerequisites

- Python 3.13.3
- [`uv`](https://docs.astral.sh/uv/) package manager
- Access to the datasets on [HuggingFace (zayanhugsAI)](https://huggingface.co/zayanhugsAI)
- API keys for your chosen LLM provider (see [Configuration](#configuration))

> **Recommendation:** Use Linux or macOS. On Windows, use [WSL](https://learn.microsoft.com/en-us/windows/wsl/install).

---

## Setup

**1. Clone the repo**

```bash
git clone <repo-url>
cd SPARQ-v2
```

**2. Install dependencies**

```bash
uv sync
```

**3. Configure environment**

Create a `.env` file in the project root:

```ini
# AWS Bedrock (authenticate via SSO before running)
AWS_PROFILE=your_aws_profile_name
AWS_REGION=us-east-1

# LangSmith tracing (optional — get key at smith.langchain.com)
LANGSMITH_API_KEY=your_langsmith_api_key
LANGSMITH_TRACING=true
LANGSMITH_PROJECT=SPARQ

# HuggingFace token (needed to download datasets)
HF_TOKEN=your_huggingface_token
```

Before each session, log in via SSO:

```bash
aws sso login --profile your_profile_name
```

**4. Download datasets**

First request access on [HuggingFace](https://huggingface.co/zayanhugsAI), then:

```bash
uv run python -m sparq.utils.download_data
```

---

## Usage

**Run with the default test query:**

```bash
uv run sparq -t
```

**Run interactively (enter your own query):**

```bash
uv run sparq
```

**Run with Docker:**

```bash
./scripts/run_scripts/run_docker.sh
```

---

## Output

Each run writes to a timestamped directory under `~/tmp/sparq_v2/`:

```
~/tmp/sparq_v2/14-04-2026_11-28-17/
├── report.md           ← structured scientific report (markdown)
├── report.pdf          ← PDF rendering (requires pandoc)
├── trace.json          ← full state snapshot for reproducibility
├── metadata.json       ← run timings and LLM config used
└── researcher/
    ├── figure_1.png    ← figures generated during analysis
    ├── figure_2.png
    └── namespace.pkl   ← persisted Python REPL namespace
```

---

## Configuration

Override model and provider per node by creating `config/config.toml` (takes precedence over defaults):

```toml
[llm_config.router]
model = "gemini-2.0-flash"
provider = "google_genai"

[llm_config.planner]
model = "gemini-2.5-pro"
provider = "google_genai"

[llm_config.researcher]
model = "claude-sonnet-4-5"
provider = "aws_bedrock"
recursion_limit = 100

[llm_config.critic]
model = "gemini-2.0-flash"
provider = "google_genai"

[llm_config.synthesizer]
model = "gemini-2.5-pro"
provider = "google_genai"

[llm_config.vision]
# Must be a multimodal model — used by the interpret_plot tool
model = "gemini-2.0-flash"
provider = "google_genai"
```

Supported providers: `google_genai`, `openai`, `aws_bedrock`, `openrouter`.

---

## Evaluation

SPARQ includes an evaluation harness for the paper's ablation studies.

**Score a single run with LLM-as-judge:**

```python
from sparq.eval.judge import judge_report
judgement = judge_report(question, report, llm_config)
print(judgement.total, judgement.rationale)  # scores: relevance, completeness, validity, clarity
```

**Batch evaluation over the full question dataset:**

```bash
uv run python -m sparq.eval.batch                    # all questions
uv run python -m sparq.eval.batch --grade-min 3      # only questions graded 3+
uv run python -m sparq.eval.batch --questions 0 3 7  # specific indices
```

**Ablation study:**

```bash
uv run python -m sparq.eval.ablation
```

Ablation configurations are defined in `src/sparq/eval/ablation.py`. Each config is a dict of setting overrides (e.g. disable critic, swap model, change provider). Results are written to `~/tmp/sparq_v2/eval/ablation/`.

---

## Datasets

| Dataset | Description |
|---------|-------------|
| **PulseNet** | CDC whole-genome sequencing isolate data for Salmonella and other pathogens |
| **NORS** | National Outbreak Reporting System — foodborne illness outbreaks |
| **SVI** | CDC Social Vulnerability Index — county-level socioeconomic indicators |
| **Map the Meal Gap** | Feeding America food insecurity estimates by county |
| **Census Population** | US Census population estimates |

All datasets are downloaded from [HuggingFace (zayanhugsAI)](https://huggingface.co/zayanhugsAI) and cached locally.

---

## Development

```bash
# Run all tests
uv run python -m unittest

# Run a specific test module
uv run python -m unittest tests.tools.test_executor

# Run tests (via script)
./scripts/run_scripts/run_tests.sh
```

See [CHANGES.md](CHANGES.md) for a full account of what changed between v1 and v2.
See [docs/architecture.md](docs/architecture.md) for a detailed architecture reference.
See [requirements.md](requirements.md) for the full system specification.
