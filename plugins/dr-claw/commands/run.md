---
description: Execute the next pipeline task, a specific task, or all remaining tasks
argument-hint: '[next|all|<task-id>]'
allowed-tools: [Read, Write, Glob, Grep, Bash]
---

You are executing Dr. Claw research pipeline tasks.

## Determine what to run

Parse $ARGUMENTS:
- If empty or "next": execute only the next pending task
- If "all": loop through ALL pending tasks sequentially
- Otherwise: treat as a task-id and execute that specific task

## For each task to execute:

1. **Read current state**: Run `node "${CLAUDE_PLUGIN_ROOT}/scripts/read-tasks.mjs" --next --json` to get the next pending task (or use the specific task-id).

2. **Read the task definition**: The JSON includes `id`, `stage`, `title`, `description`, `skill`, `outputs`.

3. **Check dependencies**: If any dependency task is not "done", skip and report it as blocked.

4. **Load the skill**: Read `${CLAUDE_PLUGIN_ROOT}/skills/{task.skill}/SKILL.md`. If the skill directory doesn't exist, inform the user and proceed with the task description alone.

5. **Execute**: Follow the skill instructions to complete the task. Use the project context from `.pipeline/docs/research_brief.json`. Write outputs to the paths specified in `task.outputs` (relative to `.pipeline/`).

6. **Mark done**: Run `node "${CLAUDE_PLUGIN_ROOT}/scripts/update-task.mjs" --task-id={task.id} --status=done`

7. **Report**: Print what was accomplished and what the next task is.

8. **If mode is "all"**: Repeat from step 1 for the next pending task. Stop when no pending tasks remain.

## On failure

If a task fails, mark it as "failed" via:
```
node "${CLAUDE_PLUGIN_ROOT}/scripts/update-task.mjs" --task-id={task.id} --status=failed
```
Report the error. Do NOT continue to the next task in "all" mode — ask the user how to proceed.
