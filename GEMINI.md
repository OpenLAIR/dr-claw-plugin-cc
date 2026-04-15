# GEMINI.md

## Project Overview

This is the **Dr. Claw Plugin for Claude Code** (`OpenLAIR/dr-claw-plugin-cc`). It packages the Dr. Claw AI research pipeline as a terminal plugin with slash commands, bundled skills, and auto-detection.

While this plugin targets Claude Code, the research pipeline behavior it implements is agent-agnostic. This file ensures Gemini CLI maintains the same understanding when working on this codebase.

## Architecture

```
plugins/dr-claw/
├── .claude-plugin/plugin.json   # Plugin manifest (Claude Code specific)
├── commands/                    # Slash commands (setup, status, run, reset)
├── hooks/hooks.json             # SessionStart auto-detection hook
├── skills/                      # 60+ bundled research skills (agent-agnostic Markdown)
├── scripts/                     # Node.js helpers (detect-pipeline, read-tasks, update-task)
└── templates/                   # Task templates for project types (JSON)
```

## Tool Mapping

Gemini CLI equivalents for Claude Code tools referenced in commands:

| Claude Code | Gemini CLI |
|-------------|-----------|
| Read | read_file |
| Write | write_file |
| Edit | edit_file |
| Bash | run_shell |
| Glob | run_shell (with find/ls) |
| Grep | run_shell (with grep/rg) |

## Development Guidelines

### Commands (commands/*.md)
- Markdown with YAML frontmatter. These are Claude Code slash command definitions.
- When modifying, ensure the research logic is portable — avoid Claude-Code-only patterns.
- `${CLAUDE_PLUGIN_ROOT}` is a Claude Code variable; in Gemini context, resolve manually.

### Skills (skills/**/SKILL.md)
- Agent-agnostic Markdown procedures. These work with any agent.
- Synced from main `dr-claw` repo. Do not edit directly here.

### Scripts (scripts/*.mjs)
- Node.js ESM, runnable from any agent via shell execution.
- Use `process.env.CLAUDE_PROJECT_DIR || process.cwd()` for project root.

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
- Update `tasks.json` status after each task.
- Update `research_brief.json` with produced artifacts.
- Confirm at stage transitions.
- Never fabricate references, results, or citations.

### Skill Resolution
Skills in `plugins/dr-claw/skills/`. Read `SKILL.md` and follow procedures exactly.

## Rules
- **SANDBOX**: Never access files outside user's project directory at runtime.
- **No PII**: No personal paths, usernames, or credentials in code.
- **Consistency**: Behavior changes must update ALL config files (CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules).
- **Portable**: Skills and scripts should work across Claude Code, Gemini CLI, and Codex. Avoid agent-specific APIs in shared code.
