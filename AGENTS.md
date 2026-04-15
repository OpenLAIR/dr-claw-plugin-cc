# AGENTS.md

## Project Overview

This is the **Dr. Claw Plugin for Claude Code** (`OpenLAIR/dr-claw-plugin-cc`). It packages the Dr. Claw AI research pipeline as a terminal plugin with slash commands, bundled skills, and auto-detection.

## Architecture

```
plugins/dr-claw/
├── .claude-plugin/plugin.json   # Plugin manifest
├── commands/                    # Slash commands (setup, status, run, reset)
├── hooks/hooks.json             # SessionStart auto-detection
├── skills/                      # 60+ bundled research skills
├── scripts/                     # Node.js helpers (detect-pipeline, read-tasks, update-task)
└── templates/                   # Task templates for project types
```

## Development Guidelines

### Commands (commands/*.md)
- Markdown with YAML frontmatter defining agent behavior per slash command.
- `$ARGUMENTS` = user input after command name.
- `${CLAUDE_PLUGIN_ROOT}` = `plugins/dr-claw/` at runtime.
- Reference scripts via `node "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.mjs"`.

### Skills (skills/**/SKILL.md)
- Synced from main `dr-claw` repo via `scripts/sync-skills.mjs`. Do not edit directly.
- Exception: plugin-only skills not in main repo.

### Scripts (scripts/*.mjs)
- Node.js ESM. Read/write `.pipeline/` in user's project directory.
- Use `process.env.CLAUDE_PROJECT_DIR || process.cwd()` for project root.
- Thin wrappers for file I/O only.

## Research Pipeline Spec

All agent integrations must implement this behavior consistently.

### Pipeline Stages
```
Survey → Ideation → Experiment → Publication → Promotion
```

### Key Files (user's project)
- `.pipeline/docs/research_brief.json` — Project definition
- `.pipeline/tasks/tasks.json` — Task list with statuses
- `.pipeline/config.json` — Pipeline config
- `instance.json` — Path mapping for pipeline directories

### State Contract
- Update `tasks.json` status after each task completion.
- Update `research_brief.json` with produced artifacts.
- Confirm at stage transitions before proceeding.
- Never fabricate references, results, or citations.

### Skill Resolution
Skills in `plugins/dr-claw/skills/`. Read `SKILL.md` and follow procedures exactly.

## Rules
- **SANDBOX**: Never access files outside user's project directory at runtime.
- **No PII**: No personal paths, usernames, or credentials in code.
- **Consistency**: Behavior changes must update ALL config files (CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules).
- **Test**: After modifying commands, test with `cc --plugin-dir plugins/dr-claw`.
