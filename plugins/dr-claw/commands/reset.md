---
description: Reset pipeline task statuses back to pending
argument-hint: '[all|<stage>|<task-id>]'
allowed-tools: [Bash]
---

Parse $ARGUMENTS to determine what to reset:
- If "all": reset every task
- If a known stage name (Survey, Ideation, Experiment, Publication, Promotion): reset that stage
- Otherwise: treat as a task-id

For "all" or a stage name:
!`node "${CLAUDE_PLUGIN_ROOT}/scripts/update-task.mjs" --stage=$ARGUMENTS --status=pending`

For a specific task-id:
!`node "${CLAUDE_PLUGIN_ROOT}/scripts/update-task.mjs" --task-id=$ARGUMENTS --status=pending`

After reset, show updated status:
!`node "${CLAUDE_PLUGIN_ROOT}/scripts/read-tasks.mjs"`
