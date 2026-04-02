---
name: drclaw-run
description: |
  This skill should be used when the user says "run the next task", "execute task",
  "continue pipeline", "start the experiment", or any request to advance the research pipeline.
---

# Executing a Pipeline Task

When executing a Dr. Claw pipeline task:

1. Read the task from `.pipeline/tasks/tasks.json`
2. Check all dependencies are marked "done"
3. Read the skill referenced by the task: look for the skill in the plugin's skills directory
4. Read the project context from `.pipeline/docs/research_brief.json`
5. Follow the skill's instructions, adapted to the project context
6. Write outputs to the paths in `task.outputs` (relative to `.pipeline/`)
7. Update the task status to "done"

## Important Rules

- Always read research_brief.json first for project context
- Write ALL outputs to the `.pipeline/` directory structure
- Never skip a task's dependencies — report blocked tasks
- If a skill references other skills, those are available in the plugin's skills directory
- Report what you accomplished after each task
- On failure, mark the task as "failed" and report the error
