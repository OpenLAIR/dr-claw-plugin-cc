---
description: Initialize a Dr. Claw research pipeline in the current directory
allowed-tools: [Read, Write, Glob, Bash, Grep]
---

You are initializing a Dr. Claw research project. Walk the user through an interactive wizard, asking ONE question at a time. After gathering all answers, generate the pipeline files.

IMPORTANT: Do NOT run any tools or commands before asking questions. Start immediately with the first question below. Only use tools in Step 6 after all answers are collected.

## Step 1: Project Type

Ask the user:
> What type of research project is this?
> 1. **Method/Model** — algorithmic, architectural, or model innovation
> 2. **Dataset** — benchmark creation, data curation, or evaluation suite
> 3. **Position Paper** — survey, opinion, or perspective paper

Wait for their answer before proceeding.

## Step 2: Research Topic

Ask:
> What is the research topic or title? (e.g., "LLM watermarking for copyright protection")

## Step 3: Target Venue

Ask:
> What is the target venue? (e.g., NeurIPS 2026, ICML 2026, ACL 2026, ICLR 2026, or "none")

## Step 4: Research Goal / Hypothesis

Ask:
> What is the main research question or hypothesis?

## Step 5: Key Constraints (optional)

Ask:
> Any constraints? (compute budget, timeline, team size — or just press Enter to skip)

## Step 6: Generate Pipeline

After gathering all answers:

1. Read the matching template from `${CLAUDE_PLUGIN_ROOT}/templates/`:
   - Method/Model → `tasks-ai-research-method.json`
   - Dataset → `tasks-ai-research-dataset.json`
   - Position Paper → `tasks-ai-research-position-paper.json`

2. Read the brief template from `${CLAUDE_PLUGIN_ROOT}/templates/research_brief.template.json`

3. Fill in `research_brief.json` with user answers:
   - `meta.title` = research topic
   - `meta.target_venue` = venue
   - `meta.project_type` = project type choice
   - `meta.created_at` = current ISO date
   - `sections.ideation.research_goal` = hypothesis/question

4. Create the full directory structure using Bash:
   ```bash
   mkdir -p .pipeline/docs .pipeline/tasks .pipeline/Survey/reports .pipeline/Ideation/ideas .pipeline/Ideation/references .pipeline/Experiment/core_code .pipeline/Experiment/analysis .pipeline/Publication/paper .pipeline/Promotion/slides .pipeline/Promotion/video
   ```

5. Write `.pipeline/docs/research_brief.json` with the filled template
6. Write `.pipeline/tasks/tasks.json` with the task list from the matching template

7. Print a summary:

> ✓ Dr. Claw pipeline initialized!
>
>   Project:  {title}
>   Type:     {type}
>   Venue:    {venue}
>   Tasks:    {count} tasks across 5 stages
>
>   Next steps:
>     /drclaw:status  — view pipeline progress
>     /drclaw:run     — execute the first task
