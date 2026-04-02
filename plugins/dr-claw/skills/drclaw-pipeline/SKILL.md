---
name: drclaw-pipeline
description: |
  This skill should be used when the user mentions "research pipeline", "pipeline status",
  "what stage am I in", "next task", "dr claw", or when a .pipeline/ directory is detected
  in the project. Provides awareness of the 5-stage research pipeline and routes to the
  correct skill for each task.
---

# Dr. Claw Research Pipeline

You are operating within a Dr. Claw research pipeline. The project follows a 5-stage structure:

1. **Survey** — Literature review, gap analysis, baseline mapping
2. **Ideation** — Idea generation, evaluation, resource preparation
3. **Experiment** — Code survey, implementation, analysis
4. **Publication** — Paper writing, figures, review, citation audit
5. **Promotion** — Slides, narration, video

## Pipeline Files

- `.pipeline/docs/research_brief.json` — Project definition and goals
- `.pipeline/tasks/tasks.json` — Task list with statuses
- `.pipeline/{Stage}/` — Output directories per stage

## How Tasks Work

Each task in tasks.json has:
- `id`: unique identifier
- `stage`: which pipeline stage (Survey, Ideation, etc.)
- `skill`: which skill to use (maps to a SKILL.md in this plugin)
- `status`: pending, in-progress, done, failed
- `dependencies`: task IDs that must be done first
- `outputs`: where to write results (relative to .pipeline/)

## Stage-Skill Mapping

See `references/stage-skill-map.json` for the full mapping of which skills are available per stage.

## Commands

- `/drclaw:setup` — Initialize a new research project
- `/drclaw:status` — View pipeline progress
- `/drclaw:run` — Execute tasks
- `/drclaw:reset` — Reset task statuses
