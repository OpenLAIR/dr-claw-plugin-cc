# CLAUDE.md

## Project Overview

This is the **Dr. Claw Plugin for Claude Code** — a Claude Code plugin that brings the full AI research pipeline to terminal users. It lives at `OpenLAIR/dr-claw-plugin-cc`.

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

The plugin provides four slash commands (`/drclaw:setup`, `/drclaw:status`, `/drclaw:run`, `/drclaw:reset`), a SessionStart hook for auto-detection, and bundled research skills.

## Development Guidelines

### When modifying commands (commands/*.md)
- Commands are Markdown files with YAML frontmatter. They define the agent's behavior for each slash command.
- `$ARGUMENTS` is the user's input after the command name.
- `${CLAUDE_PLUGIN_ROOT}` resolves to `plugins/dr-claw/` at runtime.
- Reference scripts via `node "${CLAUDE_PLUGIN_ROOT}/scripts/<name>.mjs"`.

### When modifying skills (skills/**/SKILL.md)
- Skills are synced from the main `dr-claw` repo via `scripts/sync-skills.mjs`.
- Do NOT edit skills directly here — edit in the main repo and re-sync.
- Exception: plugin-only skills that don't exist in the main repo.

### When modifying scripts (scripts/*.mjs)
- All scripts are Node.js ESM (`.mjs`).
- They read/write `.pipeline/` files in the user's project directory.
- Use `process.env.CLAUDE_PROJECT_DIR || process.cwd()` for the project root.
- Keep scripts thin — they do file I/O only, not research logic.

## Research Pipeline Behavior

This section defines the **canonical behavior** that all agent integrations (Claude Code, Gemini, Codex, Cursor) must implement consistently. When writing or modifying commands, skills, or agent config files, ensure alignment with this spec.

### Pipeline Stages
```
Survey → Ideation → Experiment → Publication → Promotion
```

### Key Files (in user's project directory)
- `.pipeline/docs/research_brief.json` — Project definition and goals
- `.pipeline/tasks/tasks.json` — Task list with statuses (pending, in-progress, done, failed)
- `.pipeline/config.json` — Pipeline configuration metadata
- `instance.json` — Project path mapping for pipeline directories

### State Management Contract
- After each completed task, update `tasks.json` status and `research_brief.json` with produced artifacts.
- At pipeline stage transitions, summarize what was done and confirm before proceeding.
- Never fabricate references, results, or citations.

### Skill Resolution
Skills are in `plugins/dr-claw/skills/`. Each has a `SKILL.md` with step-by-step procedures. When a task references a skill, read its SKILL.md and follow exactly.

## Rules
- **SANDBOX**: Plugin code must never access files outside the user's project directory at runtime.
- **No PII**: No personal paths, usernames, or credentials in committed code.
- **Consistency**: Any behavior change must be reflected in ALL agent config files (CLAUDE.md, AGENTS.md, GEMINI.md, .cursorrules).
- **Test commands**: After modifying a command, test it by running Claude Code with `--plugin-dir plugins/dr-claw`.
