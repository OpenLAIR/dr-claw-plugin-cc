# Task Format Reference

Each task in `.pipeline/tasks/tasks.json` follows this schema:

```json
{
  "id": "string — unique kebab-case identifier",
  "stage": "string — Survey|Ideation|Experiment|Publication|Promotion",
  "title": "string — human-readable title",
  "description": "string — what the task should accomplish",
  "skill": "string — skill directory name (maps to skills/{name}/SKILL.md)",
  "status": "string — pending|in-progress|done|failed",
  "dependencies": ["array of task IDs that must be done first"],
  "outputs": ["array of output paths relative to .pipeline/"],
  "metadata": {}
}
```

## Status Transitions

- `pending` → `in-progress` → `done` (happy path)
- `pending` → `in-progress` → `failed` (on error)
- `done` → `pending` (via /drclaw:reset)
- `failed` → `pending` (via /drclaw:reset)
