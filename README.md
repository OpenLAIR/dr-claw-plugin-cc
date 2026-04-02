# Dr. Claw Plugin for Claude Code

Run the full AI research pipeline from your terminal — no browser needed.

## Install

### Option A: From GitHub (recommended)

```bash
# 1. Add the marketplace source
/plugin marketplace add OpenLAIR/dr-claw-plugin-cc

# 2. Install the plugin
/plugin install dr-claw@dr-claw

# 3. Reload
/reload-plugins
```

### Option B: Local clone

```bash
# Clone the repo
git clone https://github.com/OpenLAIR/dr-claw-plugin-cc.git ~/dr-claw-plugin-cc

# Launch Claude Code with the plugin
cc --plugin-dir ~/dr-claw-plugin-cc/plugins/dr-claw
```

### Option C: From official marketplace (coming soon)

Once accepted into `claude-plugins-official`:
```
/plugin install dr-claw@dr-claw
```

## Quick Start

```
cd ~/my-research-project
/drclaw:setup          # Interactive wizard — asks topic, venue, hypothesis
/drclaw:status         # View pipeline progress
/drclaw:run            # Execute the next task
/drclaw:run all        # Execute all remaining tasks
```

## Commands

| Command | Description |
|---------|-------------|
| `/drclaw:setup` | Initialize a research pipeline in the current directory |
| `/drclaw:status` | Show pipeline progress across all 5 stages |
| `/drclaw:run [next\|all\|task-id]` | Execute next task, all tasks, or a specific task |
| `/drclaw:reset [all\|stage\|task-id]` | Reset task statuses back to pending |

## Pipeline Stages

```
Survey → Ideation → Experiment → Publication → Promotion
```

Each stage has tasks with skill references and dependency chains. Tasks execute sequentially, respecting dependencies.

## Project Types

`/drclaw:setup` supports three research templates:

- **Method/Model** — 13 tasks for algorithmic or architectural innovation
- **Dataset** — 14 tasks for benchmark creation or data curation
- **Position Paper** — 13 tasks for surveys or perspective papers

## What Gets Created

```
.pipeline/
├── docs/research_brief.json     # Your project definition
├── tasks/tasks.json             # Task list with statuses
├── Survey/reports/              # Literature reviews, gap analysis
├── Ideation/ideas/              # Generated and evaluated ideas
├── Experiment/core_code/        # Implementation code
├── Experiment/analysis/         # Results, figures, tables
├── Publication/paper/           # Paper draft, review reports
└── Promotion/slides/            # Presentation materials
```

## Bundled Skills

60+ research skills covering the full pipeline:

- **Survey**: deep-research, academic-researcher, dataset-discovery
- **Ideation**: idea-generation, idea-evaluation, resource-preparation
- **Experiment**: code-survey, experiment-dev, experiment-analysis
- **Publication**: paper-writing, figure-gen, paper-reviewer, reference-audit
- **Promotion**: academic-presentations
- **Infrastructure**: distributed-training, inference-serving, RAG, fine-tuning, and more

## Auto-Detection

When you open Claude Code in a directory with `.pipeline/`, the plugin automatically detects it and shows your current progress — no need to run `/drclaw:status` manually.

## Learn More

- [Dr. Claw](https://github.com/OpenLAIR/dr-claw) — The full-stack research workspace (web UI + server)
- [OpenLAIR](https://github.com/OpenLAIR) — Open Lab for AI Research
