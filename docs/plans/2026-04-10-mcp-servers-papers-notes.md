# MCP Servers: Papers Search + Notes (Obsidian) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add two MCP servers to the Dr. Claw Claude Code plugin — `drclaw-papers` for multi-source academic paper search and `drclaw-notes` for Obsidian vault operations via the Obsidian CLI — plus a companion skill doc that teaches agents how to use the notes MCP for project knowledge management workflows.

**Architecture:** Each MCP server is a standalone Node.js ESM file using `@modelcontextprotocol/sdk` with stdio transport (same pattern as the existing `mcp-compute.js` in vibelab-public). `drclaw-papers` wraps the existing `search_ai_papers.py` Python script (bundled into the plugin). `drclaw-notes` wraps the Obsidian CLI binary, with fs-based fallback for environments where Obsidian isn't installed. Both are registered in `plugin.json` under `mcpServers`. A new skill `drclaw-notes-workflows` provides the guidance layer on top of the MCP tools.

**Tech Stack:** Node.js ESM, `@modelcontextprotocol/sdk`, Python 3 (papers script), Obsidian CLI

---

### Task 1: Add MCP SDK dependency and create directory structure

**Files:**
- Create: `plugins/dr-claw/mcp-servers/papers/server.mjs`
- Create: `plugins/dr-claw/mcp-servers/notes/server.mjs`
- Create: `plugins/dr-claw/mcp-servers/papers/search_ai_papers.py`
- Modify: `plugins/dr-claw/.claude-plugin/plugin.json`
- Create: `package.json` (repo root, for the MCP SDK dependency)

**Step 1: Create package.json at repo root**

```json
{
  "name": "dr-claw-plugin-cc",
  "version": "0.2.0",
  "private": true,
  "type": "module",
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.29.0"
  }
}
```

**Step 2: Install dependency**

Run: `cd ~/dr-claw-plugin-cc && npm install`
Expected: `node_modules/` created with MCP SDK

**Step 3: Update .gitignore**

Append `node_modules/` to `.gitignore`.

**Step 4: Create directory structure**

Run:
```bash
mkdir -p plugins/dr-claw/mcp-servers/papers
mkdir -p plugins/dr-claw/mcp-servers/notes
```

**Step 5: Create placeholder files**

Create empty `server.mjs` in both directories (will be filled in Tasks 2 and 4).

**Step 6: Commit**

```bash
git add package.json .gitignore plugins/dr-claw/mcp-servers/
git commit -m "chore: add MCP SDK dependency and mcp-servers directory structure"
```

---

### Task 2: Implement `drclaw-papers` MCP server

**Files:**
- Create: `plugins/dr-claw/mcp-servers/papers/server.mjs`
- Create: `plugins/dr-claw/mcp-servers/papers/search_ai_papers.py`

**Step 1: Copy and adapt the paper search Python script**

Copy from `~/.claude/skills/searching-ai-papers/scripts/search_ai_papers.py` into `plugins/dr-claw/mcp-servers/papers/search_ai_papers.py`.

This is a 535-line self-contained script with zero pip dependencies (uses only `urllib`, `xml.etree`, `json`, `argparse`). It supports:
- `--sources arxiv,semantic_scholar,openalex,openreview,hf_daily,iclr_accepted`
- `--query`, `--max-results`, `--year-from`, `--year-to`
- `--format json` for structured output
- `--hf-date`, `--hf-week`, `--hf-month`, `--hf-sort` for HF Daily
- `--iclr-year` for accepted ICLR papers
- Built-in dedup by normalized title

No modifications needed to the Python script itself — the MCP server spawns it as a subprocess.

**Step 2: Write `server.mjs`**

```javascript
#!/usr/bin/env node
/**
 * drclaw-papers MCP Server
 *
 * Multi-source academic paper search via MCP tools.
 * Wraps search_ai_papers.py (bundled, zero pip deps).
 */
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const execFileAsync = promisify(execFile);
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCRIPT = path.join(__dirname, 'search_ai_papers.py');

const server = new Server(
  { name: 'drclaw-papers', version: '1.0.0' },
  { capabilities: { tools: {} } },
);

// ─── Tool definitions ───

const TOOLS = [
  {
    name: 'papers_search',
    description:
      'Search for academic AI/ML papers across multiple sources: arXiv, Semantic Scholar, OpenAlex, OpenReview, and Hugging Face Daily Papers. Returns deduplicated results with title, authors, year, URL, and source. Use this for literature discovery, survey building, and finding related work.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query, e.g. "graph neural networks interpretability"',
        },
        sources: {
          type: 'string',
          description:
            'Comma-separated sources to search. Options: arxiv, semantic_scholar, openalex, openreview, hf_daily, iclr_accepted. Default: all except iclr_accepted.',
          default: 'arxiv,semantic_scholar,openalex,openreview,hf_daily',
        },
        maxResults: {
          type: 'number',
          description: 'Maximum results per source (default: 20)',
          default: 20,
        },
        yearFrom: {
          type: 'number',
          description: 'Earliest publication year filter (e.g. 2023)',
        },
        yearTo: {
          type: 'number',
          description: 'Latest publication year filter (e.g. 2026)',
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'papers_trending',
    description:
      'Get trending or recent papers from Hugging Face Daily Papers. Useful for staying current with the latest research. Supports filtering by date, week, or month.',
    inputSchema: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description:
            'Optional query to filter trending papers. Leave empty for all trending papers.',
          default: '',
        },
        period: {
          type: 'string',
          description:
            'Time period: a date (YYYY-MM-DD), week (YYYY-Www e.g. 2026-W14), or month (YYYY-MM). Default: today.',
        },
        sort: {
          type: 'string',
          enum: ['trending', 'publishedAt'],
          description: 'Sort order: "trending" for hot papers, "publishedAt" for newest first.',
          default: 'trending',
        },
        maxResults: {
          type: 'number',
          description: 'Maximum results (default: 20)',
          default: 20,
        },
      },
    },
  },
  {
    name: 'papers_iclr_accepted',
    description:
      'Get accepted papers from a specific ICLR year via OpenReview. Useful for surveying what was accepted at ICLR.',
    inputSchema: {
      type: 'object',
      properties: {
        year: {
          type: 'number',
          description: 'ICLR year (e.g. 2025, 2026)',
        },
        maxResults: {
          type: 'number',
          description: 'Maximum results (default: 50)',
          default: 50,
        },
      },
      required: ['year'],
    },
  },
];

// ─── Tool handlers ───

async function runPythonSearch(args) {
  const pythonCmd = process.env.PYTHON_CMD || 'python3';
  try {
    const { stdout, stderr } = await execFileAsync(pythonCmd, args, {
      timeout: 60_000,
      maxBuffer: 10 * 1024 * 1024,
    });
    if (stderr) console.error('[drclaw-papers]', stderr);
    return stdout;
  } catch (err) {
    throw new Error(`Paper search failed: ${err.message}`);
  }
}

async function handleTool(name, args) {
  switch (name) {
    case 'papers_search': {
      const pyArgs = [
        SCRIPT,
        '--query', args.query || '',
        '--sources', args.sources || 'arxiv,semantic_scholar,openalex,openreview,hf_daily',
        '--max-results', String(args.maxResults || 20),
        '--format', 'json',
      ];
      if (args.yearFrom) pyArgs.push('--year-from', String(args.yearFrom));
      if (args.yearTo) pyArgs.push('--year-to', String(args.yearTo));
      return await runPythonSearch(pyArgs);
    }

    case 'papers_trending': {
      const pyArgs = [
        SCRIPT,
        '--sources', 'hf_daily',
        '--format', 'json',
        '--max-results', String(args.maxResults || 20),
        '--hf-sort', args.sort || 'trending',
      ];
      if (args.query) pyArgs.push('--query', args.query);
      if (args.period) {
        if (/^\d{4}-\d{2}-\d{2}$/.test(args.period)) {
          pyArgs.push('--hf-date', args.period);
        } else if (/^\d{4}-W\d{2}$/.test(args.period)) {
          pyArgs.push('--hf-week', args.period);
        } else if (/^\d{4}-\d{2}$/.test(args.period)) {
          pyArgs.push('--hf-month', args.period);
        }
      }
      return await runPythonSearch(pyArgs);
    }

    case 'papers_iclr_accepted': {
      const pyArgs = [
        SCRIPT,
        '--sources', 'iclr_accepted',
        '--iclr-year', String(args.year),
        '--max-results', String(args.maxResults || 50),
        '--format', 'json',
      ];
      return await runPythonSearch(pyArgs);
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

// ─── MCP protocol handlers ───

server.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: toolArgs } = request.params;
  try {
    const result = await handleTool(name, toolArgs || {});
    return { content: [{ type: 'text', text: result }] };
  } catch (error) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// ─── Start ───

const transport = new StdioServerTransport();
await server.connect(transport);
```

**Step 3: Commit**

```bash
git add plugins/dr-claw/mcp-servers/papers/
git commit -m "feat: add drclaw-papers MCP server for multi-source paper search"
```

---

### Task 3: Test `drclaw-papers` MCP server

**Step 1: Run the server directly to verify it starts**

Run:
```bash
cd ~/dr-claw-plugin-cc
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node plugins/dr-claw/mcp-servers/papers/server.mjs
```

Expected: JSON response listing `papers_search`, `papers_trending`, `papers_iclr_accepted`.

**Step 2: Test a paper search call**

Run:
```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"papers_search","arguments":{"query":"watermarking language models","sources":"arxiv","maxResults":3}}}' | node plugins/dr-claw/mcp-servers/papers/server.mjs
```

Expected: JSON response with paper results from arXiv.

**Step 3: Test trending papers**

Run:
```bash
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"papers_trending","arguments":{"maxResults":3}}}' | node plugins/dr-claw/mcp-servers/papers/server.mjs
```

Expected: JSON response with HF daily trending papers.

**Step 4: Fix any issues and commit**

```bash
git add -A
git commit -m "fix: adjustments from drclaw-papers testing"
```

---

### Task 4: Implement `drclaw-notes` MCP server

**Files:**
- Create: `plugins/dr-claw/mcp-servers/notes/server.mjs`

**Step 1: Write `server.mjs`**

This server wraps the Obsidian CLI (`Obsidian` binary on macOS). It detects whether the CLI is available at startup and falls back to direct filesystem operations if not.

```javascript
#!/usr/bin/env node
/**
 * drclaw-notes MCP Server
 *
 * Obsidian vault operations via MCP tools.
 * Primary backend: Obsidian CLI (requires Obsidian app running).
 * Fallback: direct filesystem read/write (no search/backlinks/tasks).
 *
 * Configure via env:
 *   OBSIDIAN_VAULT  - vault name (default: auto-detect from Obsidian)
 *   VAULT_PATH      - absolute path to vault (required for fs fallback)
 */
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import fs from 'node:fs';
import path from 'node:path';

const execFileAsync = promisify(execFile);

const VAULT_NAME = process.env.OBSIDIAN_VAULT || '';
const VAULT_PATH = process.env.VAULT_PATH || '';

// ─── Obsidian CLI detection ───

let obsidianBin = null;

async function detectObsidian() {
  // macOS: /Applications/Obsidian.app/Contents/MacOS/Obsidian
  const candidates = [
    '/Applications/Obsidian.app/Contents/MacOS/Obsidian',
    '/Applications/Obsidian.app/Contents/MacOS/obsidian',
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) {
      obsidianBin = c;
      return;
    }
  }
  // Try PATH
  try {
    await execFileAsync('which', ['Obsidian']);
    obsidianBin = 'Obsidian';
  } catch {
    try {
      await execFileAsync('which', ['obsidian']);
      obsidianBin = 'obsidian';
    } catch {
      obsidianBin = null;
    }
  }
}

async function obsidianCmd(args) {
  if (!obsidianBin) throw new Error('Obsidian CLI not available. Set VAULT_PATH env for filesystem fallback.');
  const fullArgs = VAULT_NAME ? [`vault=${VAULT_NAME}`, ...args] : args;
  try {
    const { stdout } = await execFileAsync(obsidianBin, fullArgs, {
      timeout: 15_000,
      maxBuffer: 5 * 1024 * 1024,
    });
    return stdout.trim();
  } catch (err) {
    throw new Error(`Obsidian CLI error: ${err.message}`);
  }
}

function requireVaultPath() {
  if (!VAULT_PATH) throw new Error('VAULT_PATH env not set. Required for filesystem operations.');
  return VAULT_PATH;
}

// ─── Tool definitions ───

const TOOLS = [
  {
    name: 'notes_read',
    description: 'Read the content of a note from the Obsidian vault. Provide either a file name (resolved like a wikilink) or an exact path from vault root.',
    inputSchema: {
      type: 'object',
      properties: {
        file: { type: 'string', description: 'Note name (wikilink-style resolution, no path or extension needed)' },
        path: { type: 'string', description: 'Exact path from vault root, e.g. "Projects/Active/index.md"' },
      },
    },
  },
  {
    name: 'notes_create',
    description: 'Create a new note in the Obsidian vault. The note will NOT open in Obsidian (silent mode). Use notes_open separately if needed.',
    inputSchema: {
      type: 'object',
      properties: {
        name: { type: 'string', description: 'Note name (without .md extension)' },
        content: { type: 'string', description: 'Note content (markdown). Use \\n for newlines.' },
        folder: { type: 'string', description: 'Target folder path from vault root (e.g. "Projects/Active"). Created if needed.' },
        overwrite: { type: 'boolean', description: 'Overwrite if note already exists (default: false)', default: false },
      },
      required: ['name', 'content'],
    },
  },
  {
    name: 'notes_append',
    description: 'Append content to an existing note.',
    inputSchema: {
      type: 'object',
      properties: {
        file: { type: 'string', description: 'Note name' },
        path: { type: 'string', description: 'Exact path from vault root' },
        content: { type: 'string', description: 'Content to append' },
      },
      required: ['content'],
    },
  },
  {
    name: 'notes_search',
    description: 'Full-text search across the vault. Returns matching notes with context. Requires Obsidian CLI (no filesystem fallback).',
    inputSchema: {
      type: 'object',
      properties: {
        query: { type: 'string', description: 'Search query' },
        limit: { type: 'number', description: 'Max results (default: 10)', default: 10 },
      },
      required: ['query'],
    },
  },
  {
    name: 'notes_list',
    description: 'List notes in a vault folder. Returns file names and paths.',
    inputSchema: {
      type: 'object',
      properties: {
        folder: { type: 'string', description: 'Folder path from vault root (e.g. "Projects/Active"). Empty for vault root.' },
        recursive: { type: 'boolean', description: 'Include subfolders (default: false)', default: false },
      },
    },
  },
  {
    name: 'notes_open',
    description: 'Open a note in Obsidian in a new tab. Requires Obsidian to be running.',
    inputSchema: {
      type: 'object',
      properties: {
        file: { type: 'string', description: 'Note name' },
        path: { type: 'string', description: 'Exact path from vault root' },
      },
    },
  },
  {
    name: 'notes_backlinks',
    description: 'List all notes that link to the specified note. Requires Obsidian CLI.',
    inputSchema: {
      type: 'object',
      properties: {
        file: { type: 'string', description: 'Note name' },
        path: { type: 'string', description: 'Exact path from vault root' },
      },
    },
  },
  {
    name: 'notes_tags',
    description: 'List all tags in the vault, or tags for a specific note. Requires Obsidian CLI.',
    inputSchema: {
      type: 'object',
      properties: {
        file: { type: 'string', description: 'Optional: note name to get tags for. Omit for vault-wide tag list.' },
      },
    },
  },
  {
    name: 'notes_tasks',
    description: 'List tasks (checkboxes) from the vault. Can filter by done/todo. Requires Obsidian CLI.',
    inputSchema: {
      type: 'object',
      properties: {
        filter: {
          type: 'string',
          enum: ['todo', 'done', 'all'],
          description: 'Filter: "todo" (incomplete), "done" (complete), "all"',
          default: 'todo',
        },
        file: { type: 'string', description: 'Optional: limit to a specific note' },
      },
    },
  },
  {
    name: 'notes_properties',
    description: 'Get frontmatter properties (YAML) for a note. Requires Obsidian CLI.',
    inputSchema: {
      type: 'object',
      properties: {
        file: { type: 'string', description: 'Note name' },
        path: { type: 'string', description: 'Exact path from vault root' },
      },
    },
  },
  {
    name: 'notes_property_set',
    description: 'Set a frontmatter property on a note. Requires Obsidian CLI.',
    inputSchema: {
      type: 'object',
      properties: {
        file: { type: 'string', description: 'Note name' },
        path: { type: 'string', description: 'Exact path from vault root' },
        name: { type: 'string', description: 'Property name' },
        value: { type: 'string', description: 'Property value' },
      },
      required: ['name', 'value'],
    },
  },
  {
    name: 'notes_vault_info',
    description: 'Get information about the vault: name, path, file count, folder count.',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
];

// ─── Tool handlers ───

async function handleTool(name, args) {
  switch (name) {
    case 'notes_read': {
      if (obsidianBin) {
        const target = args.file ? [`file=${args.file}`] : [`path=${args.path}`];
        return await obsidianCmd(['read', ...target]);
      }
      // fs fallback
      const vaultRoot = requireVaultPath();
      const filePath = args.path
        ? path.join(vaultRoot, args.path)
        : path.join(vaultRoot, `${args.file}.md`);
      return fs.readFileSync(filePath, 'utf8');
    }

    case 'notes_create': {
      if (obsidianBin) {
        const cmdArgs = ['create', `name=${args.name}`, `content=${args.content}`, 'silent'];
        if (args.overwrite) cmdArgs.push('overwrite');
        return await obsidianCmd(cmdArgs);
      }
      // fs fallback
      const vaultRoot = requireVaultPath();
      const folder = args.folder || '';
      const dir = path.join(vaultRoot, folder);
      fs.mkdirSync(dir, { recursive: true });
      const filePath = path.join(dir, `${args.name}.md`);
      if (!args.overwrite && fs.existsSync(filePath)) {
        throw new Error(`Note "${args.name}" already exists. Use overwrite: true to replace.`);
      }
      fs.writeFileSync(filePath, args.content.replace(/\\n/g, '\n'), 'utf8');
      return `Created: ${path.relative(vaultRoot, filePath)}`;
    }

    case 'notes_append': {
      if (obsidianBin) {
        const target = args.file ? [`file=${args.file}`] : [`path=${args.path}`];
        return await obsidianCmd(['append', ...target, `content=${args.content}`]);
      }
      // fs fallback
      const vaultRoot = requireVaultPath();
      const filePath = args.path
        ? path.join(vaultRoot, args.path)
        : path.join(vaultRoot, `${args.file}.md`);
      fs.appendFileSync(filePath, '\n' + args.content.replace(/\\n/g, '\n'), 'utf8');
      return `Appended to: ${path.relative(vaultRoot, filePath)}`;
    }

    case 'notes_search': {
      if (!obsidianBin) throw new Error('notes_search requires Obsidian CLI. Not available in filesystem fallback mode.');
      return await obsidianCmd(['search', `query=${args.query}`, `limit=${args.limit || 10}`, 'format=json']);
    }

    case 'notes_list': {
      if (obsidianBin) {
        const cmdArgs = ['list'];
        if (args.folder) cmdArgs.push(`path=${args.folder}`);
        cmdArgs.push('format=json');
        return await obsidianCmd(cmdArgs);
      }
      // fs fallback
      const vaultRoot = requireVaultPath();
      const dir = path.join(vaultRoot, args.folder || '');
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      const results = [];
      for (const e of entries) {
        if (e.name.startsWith('.')) continue;
        const relPath = path.join(args.folder || '', e.name);
        results.push({ name: e.name, path: relPath, type: e.isDirectory() ? 'folder' : 'file' });
      }
      return JSON.stringify(results, null, 2);
    }

    case 'notes_open': {
      if (!obsidianBin) throw new Error('notes_open requires Obsidian app to be running.');
      const target = args.file ? [`file=${args.file}`] : [`path=${args.path}`];
      return await obsidianCmd(['open', 'newtab', ...target]);
    }

    case 'notes_backlinks': {
      if (!obsidianBin) throw new Error('notes_backlinks requires Obsidian CLI.');
      const target = args.file ? [`file=${args.file}`] : [`path=${args.path}`];
      return await obsidianCmd(['backlinks', ...target, 'format=json']);
    }

    case 'notes_tags': {
      if (!obsidianBin) throw new Error('notes_tags requires Obsidian CLI.');
      const cmdArgs = ['tags', 'format=json', 'counts'];
      if (args.file) cmdArgs.push(`file=${args.file}`);
      return await obsidianCmd(cmdArgs);
    }

    case 'notes_tasks': {
      if (!obsidianBin) throw new Error('notes_tasks requires Obsidian CLI.');
      const cmdArgs = ['tasks', 'format=json'];
      if (args.filter === 'todo') cmdArgs.push('todo');
      else if (args.filter === 'done') cmdArgs.push('done');
      if (args.file) cmdArgs.push(`file=${args.file}`);
      return await obsidianCmd(cmdArgs);
    }

    case 'notes_properties': {
      if (!obsidianBin) throw new Error('notes_properties requires Obsidian CLI.');
      const target = args.file ? [`file=${args.file}`] : [`path=${args.path}`];
      return await obsidianCmd(['properties', ...target, 'format=json']);
    }

    case 'notes_property_set': {
      if (!obsidianBin) throw new Error('notes_property_set requires Obsidian CLI.');
      const target = args.file ? [`file=${args.file}`] : args.path ? [`path=${args.path}`] : [];
      return await obsidianCmd(['property:set', `name=${args.name}`, `value=${args.value}`, ...target]);
    }

    case 'notes_vault_info': {
      if (obsidianBin) {
        const info = await obsidianCmd(['vault']);
        return info;
      }
      const vaultRoot = requireVaultPath();
      return JSON.stringify({ path: vaultRoot, backend: 'filesystem' });
    }

    default:
      throw new Error(`Unknown tool: ${name}`);
  }
}

// ─── MCP protocol handlers ───

const mcpServer = new Server(
  { name: 'drclaw-notes', version: '1.0.0' },
  { capabilities: { tools: {} } },
);

mcpServer.setRequestHandler(ListToolsRequestSchema, async () => ({ tools: TOOLS }));

mcpServer.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: toolArgs } = request.params;
  try {
    const result = await handleTool(name, toolArgs || {});
    return { content: [{ type: 'text', text: result }] };
  } catch (error) {
    return {
      content: [{ type: 'text', text: `Error: ${error.message}` }],
      isError: true,
    };
  }
});

// ─── Start ───

await detectObsidian();
const transport = new StdioServerTransport();
await mcpServer.connect(transport);
```

**Step 2: Commit**

```bash
git add plugins/dr-claw/mcp-servers/notes/
git commit -m "feat: add drclaw-notes MCP server wrapping Obsidian CLI"
```

---

### Task 5: Test `drclaw-notes` MCP server

**Step 1: Run the server to verify it starts and detects Obsidian**

Run:
```bash
cd ~/dr-claw-plugin-cc
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | node plugins/dr-claw/mcp-servers/notes/server.mjs
```

Expected: JSON listing all 12 notes tools.

**Step 2: Test vault info**

Run:
```bash
echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"notes_vault_info","arguments":{}}}' | OBSIDIAN_VAULT=kobo-note node plugins/dr-claw/mcp-servers/notes/server.mjs
```

Expected: Vault name, path, and file count from Obsidian CLI.

**Step 3: Test notes_search**

Run:
```bash
echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"notes_search","arguments":{"query":"research project","limit":3}}}' | OBSIDIAN_VAULT=kobo-note node plugins/dr-claw/mcp-servers/notes/server.mjs
```

Expected: JSON with matching notes.

**Step 4: Test fs fallback (no Obsidian)**

Run:
```bash
echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"notes_list","arguments":{"folder":""}}}' | VAULT_PATH=/tmp/test-vault node plugins/dr-claw/mcp-servers/notes/server.mjs
```

Set up a test vault first: `mkdir -p /tmp/test-vault && echo "# Test" > /tmp/test-vault/test.md`

Expected: JSON listing `test.md`.

**Step 5: Fix any issues and commit**

```bash
git add -A
git commit -m "fix: adjustments from drclaw-notes testing"
```

---

### Task 6: Create `drclaw-notes-workflows` skill

**Files:**
- Create: `plugins/dr-claw/skills/drclaw-notes-workflows/SKILL.md`

**Step 1: Write the skill**

This skill teaches agents HOW to use the `drclaw-notes` MCP tools to accomplish common knowledge management workflows — especially dumping project docs and research knowledge into Obsidian in a structured way.

```markdown
---
name: drclaw-notes-workflows
description: >-
  Use when the user wants to save project knowledge, research findings, paper notes, experiment
  results, or any project documentation into their Obsidian vault. Provides structured workflows
  on top of the drclaw-notes MCP tools. Triggers: "save to obsidian", "dump to notes",
  "persist knowledge", "create project notes", "update my notes with this".
---

# Dr. Claw Notes Workflows

Use the `drclaw-notes` MCP tools (notes_create, notes_read, notes_search, notes_append, etc.)
to manage research knowledge in the user's Obsidian vault. This skill defines WHAT to do;
the MCP tools handle HOW.

## Prerequisites

- The `drclaw-notes` MCP server must be available (check with `notes_vault_info`)
- The user must have configured their vault (OBSIDIAN_VAULT env or VAULT_PATH)

## Workflow 1: Persist Project Context

When a research project reaches a milestone or the user wants to save progress:

1. Call `notes_search` with the project name to check if a project folder exists
2. If not found, call `notes_create` to create the project index:
   - Path: `Projects/Active/<ProjectName>/<ProjectName>.md`
   - Content: minimal index with links to subpages
3. Create subpages for each artifact:
   - `system-design.md` — architecture decisions, technical approach
   - `progress.md` — timeline of what was done and current state
   - `key-links.md` — GitHub repo, server paths, Overleaf, conda env
4. Call `notes_property_set` to add frontmatter: `status: active`, `created: YYYY-MM-DD`

### Index Page Format (keep minimal)

```
# ProjectName

- [[system-design]]
- [[progress]]
- [[key-links]]
- [[experiment-log]]
```

### Subpage Format (detailed content here)

```
# Subpage Title

## Summary (brief)

Key points here.

---

## Full Content

Detailed content below...
```

## Workflow 2: Save Paper Notes

When the user has read or discussed a paper and wants to persist notes:

1. Call `notes_search` to check if notes for this paper exist
2. If not, call `notes_create`:
   - Path: `Papers/<Paper Title>.md`
   - Frontmatter: `title`, `authors`, `year`, `venue`, `url`
   - Content: key findings, methods, relevance to current work
3. If the paper relates to an active project, call `notes_append` on the project index
   to add a link: `- [[Papers/Paper Title|Paper Title (Year)]]`

## Workflow 3: Dump Research Findings

When experiment results, survey findings, or analysis outputs need to be saved:

1. Determine the project and artifact type
2. Call `notes_read` on the project's `experiment-log.md` (or create if missing)
3. Call `notes_append` to add a dated entry:
   ```
   ## YYYY-MM-DD: [Experiment Name]

   **Config:** [key parameters]
   **Result:** [metrics]
   **Takeaway:** [one sentence]
   ```
4. If the result is significant, also update `progress.md`

## Workflow 4: Cross-Reference Between Notes

After creating or updating notes:

1. Add `[[wikilinks]]` to related notes
2. Use `notes_backlinks` to discover existing connections
3. Use `notes_tags` to find thematically related notes

## Workflow 5: Quick Capture

When the user wants to quickly save something without structure:

1. Call `notes_create` with path `Inbox/<title>.md`
2. Content: raw dump of the information
3. The user will organize it later

## Rules

- Index pages = MINIMAL (just links). Subpages = STRUCTURED (detailed content).
- Always check if a note exists before creating (use notes_search or notes_read).
- Use wikilinks `[[Note Name]]` for internal cross-references.
- Prefer appending to existing notes over creating new ones for the same topic.
- After creating/appending, offer to open the note with `notes_open`.
- Dates use ISO format: YYYY-MM-DD.
```

**Step 2: Commit**

```bash
git add plugins/dr-claw/skills/drclaw-notes-workflows/
git commit -m "feat: add drclaw-notes-workflows skill for knowledge management guidance"
```

---

### Task 7: Register MCP servers in plugin.json

**Files:**
- Modify: `plugins/dr-claw/.claude-plugin/plugin.json`

**Step 1: Update plugin.json**

```json
{
  "name": "dr-claw",
  "version": "0.2.0",
  "description": "AI research pipeline — run end-to-end research from your terminal",
  "author": {
    "name": "OpenLAIR",
    "url": "https://github.com/OpenLAIR"
  },
  "homepage": "https://github.com/OpenLAIR/dr-claw",
  "repository": "https://github.com/OpenLAIR/dr-claw-plugin-cc",
  "license": "GPL-3.0-only",
  "keywords": ["research", "pipeline", "survey", "experiment", "paper-writing", "mcp"],
  "mcpServers": {
    "drclaw-papers": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/papers/server.mjs"]
    },
    "drclaw-notes": {
      "command": "node",
      "args": ["${CLAUDE_PLUGIN_ROOT}/mcp-servers/notes/server.mjs"],
      "env": {
        "OBSIDIAN_VAULT": "",
        "VAULT_PATH": ""
      }
    }
  }
}
```

Note: Check whether Claude Code plugin system supports `mcpServers` in `plugin.json`. If it uses a different registration mechanism, this task will need to adapt to the actual plugin spec. The `${CLAUDE_PLUGIN_ROOT}` variable should resolve to the plugin directory at runtime.

**Step 2: Commit**

```bash
git add plugins/dr-claw/.claude-plugin/plugin.json
git commit -m "feat: register drclaw-papers and drclaw-notes MCP servers in plugin manifest"
```

---

### Task 8: Update README with MCP documentation

**Files:**
- Modify: `README.md`

**Step 1: Update README**

Add an "MCP Servers" section after the existing "Commands" section:

```markdown
## MCP Servers

This plugin bundles two MCP servers that provide tool-level access to research capabilities.
Any AI agent that supports MCP (Claude Code, Codex, Gemini CLI) can use these tools directly.

### drclaw-papers

Multi-source academic paper search.

| Tool | Description |
|------|-------------|
| `papers_search` | Search arXiv, Semantic Scholar, OpenAlex, OpenReview, HF Daily Papers |
| `papers_trending` | Get trending papers from Hugging Face Daily Papers |
| `papers_iclr_accepted` | Get accepted ICLR papers by year |

No API keys required. Uses only public APIs. Requires Python 3.

### drclaw-notes

Obsidian vault operations for research knowledge management.

| Tool | Description |
|------|-------------|
| `notes_create` | Create a note |
| `notes_read` | Read a note |
| `notes_append` | Append content to a note |
| `notes_search` | Full-text search (requires Obsidian CLI) |
| `notes_list` | List notes in a folder |
| `notes_open` | Open note in Obsidian (new tab) |
| `notes_backlinks` | List backlinks to a note |
| `notes_tags` | List tags |
| `notes_tasks` | List tasks/checkboxes |
| `notes_properties` | Get frontmatter properties |
| `notes_property_set` | Set a frontmatter property |
| `notes_vault_info` | Vault information |

**Configuration:**
- Set `OBSIDIAN_VAULT` to your vault name (e.g. `my-vault`)
- Or set `VAULT_PATH` to the absolute path for filesystem-only mode
- Full features require the [Obsidian CLI](https://help.obsidian.md/cli) (Obsidian v1.8+)
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add MCP servers documentation to README"
```

---

### Task 9: Push and verify

**Step 1: Push all changes**

```bash
cd ~/dr-claw-plugin-cc
git push origin main
```

**Step 2: Verify the plugin still installs correctly**

Test local installation in a Claude Code session:
```bash
claude --plugin-dir ~/dr-claw-plugin-cc/plugins/dr-claw
```

Verify:
- Existing slash commands (`/drclaw:setup`, `/drclaw:status`, etc.) still work
- MCP servers are registered and tools appear

**Step 3: Test MCP tools from within Claude Code**

In a Claude Code session with the plugin loaded:
- Ask "search for papers about LLM watermarking" → should invoke `papers_search`
- Ask "save these findings to my Obsidian vault" → should invoke `notes_create`

---

## File Summary

| File | Action | Lines (approx) |
|------|--------|----------------|
| `package.json` | Create | 8 |
| `.gitignore` | Modify | +1 |
| `plugins/dr-claw/mcp-servers/papers/server.mjs` | Create | 180 |
| `plugins/dr-claw/mcp-servers/papers/search_ai_papers.py` | Copy | 535 |
| `plugins/dr-claw/mcp-servers/notes/server.mjs` | Create | 280 |
| `plugins/dr-claw/skills/drclaw-notes-workflows/SKILL.md` | Create | 110 |
| `plugins/dr-claw/.claude-plugin/plugin.json` | Modify | 25 |
| `README.md` | Modify | +40 |
