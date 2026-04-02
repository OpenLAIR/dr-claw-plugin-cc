---
name: nano-banana
description: >-
  Render images from text prompts via PaperBanana (multi-agent academic figure
  pipeline) or Gemini CLI's nanobanana extension. Use when the user asks to
  "render a figure", "generate an image from prompt", "create a diagram image",
  "nanobanana render", "paperbanana", or wants to turn a text prompt into an
  actual PNG image. Pairs with nanobanana-prompt-architect for end-to-end
  academic figure generation.
---

# Nano Banana — Academic Figure Rendering

## Goal & Scope

Render a text prompt into a publication-quality image file. This skill is the **rendering engine** — it takes a text prompt (typically produced by `nanobanana-prompt-architect` or directly from paper context) and produces a PNG image.

**Primary backend**: PaperBanana (`paperbanana` CLI/MCP) — multi-agent pipeline with input optimization, iterative refinement, and VLM-based critique.
**Fallback backend**: Gemini CLI nanobanana extension — simpler single-shot generation.

## Prerequisites

### PaperBanana (recommended)

- **Install**: `pip install paperbanana` or use via `uvx --from paperbanana`
- **API key**: Set `GOOGLE_API_KEY` env var (free Gemini key from https://aistudio.google.com/app/apikey)
  - Or `OPENAI_API_KEY` for OpenAI provider
- **MCP server** (for Claude Code integration): Already configured. Uses `generate_diagram` and `generate_plot` MCP tools.
- **CLI**: `paperbanana generate --input <file> --caption "<caption>" [--output <path>]`
- **Repo**: https://github.com/llmsresearch/paperbanana.git

### Gemini CLI nanobanana (fallback)

- **Gemini CLI** installed (`gemini --version`)
- **Nanobanana extension**: `gemini extensions install https://github.com/gemini-cli-extensions/nanobanana`
- **API key**: `GEMINI_API_KEY` env var (same Gemini key works)

## Algorithm

### 1. Receive the prompt

Accept one of:
- A raw text prompt string provided by the user
- A path to a markdown file containing an SOP-formatted prompt (e.g., `figure1_prompt.md`)
- A path to a methodology text file (for PaperBanana)
- An inline SOP code block from `nanobanana-prompt-architect` output

If given a file path, read the file and extract the prompt text from the first fenced code block (or use the entire content if no code block is found).

### 2. Choose rendering backend

| Condition | Backend | Why |
|-----------|---------|-----|
| PaperBanana MCP tool available | PaperBanana MCP | Best quality, multi-agent refinement |
| `paperbanana` CLI available | PaperBanana CLI | Same quality, no MCP dependency |
| Only Gemini CLI + nanobanana | Gemini nanobanana | Simpler, single-shot |
| Nothing available | Prompt-only | Save prompt, instruct user to install |

### 3a. Render via PaperBanana (preferred)

**Via MCP tool** (if `generate_diagram` MCP tool is available):
```
Call MCP tool: generate_diagram
  source_context: <methodology text or prompt>
  caption: <figure caption>
  iterations: 3
```

**Via CLI** (fallback):
```bash
# Save prompt to a temp file first
paperbanana generate \
  --input <prompt_file> \
  --caption "<caption text>" \
  --output <target_path>
```

PaperBanana saves output to `outputs/run_<timestamp>/final_output.png` by default.
Move to target: `mv outputs/run_*/final_output.png <target_path>`

### 3b. Render via Gemini CLI nanobanana (fallback)

```bash
gemini -y -p "Use the generate_image tool to create this image: <prompt_text>"
```

Images saved to `./nanobanana-output/`. Move to target path.

### 4. Locate and move the output

After rendering:
1. Find the generated image file
2. Move/copy to the target location (e.g., `Publication/paper/figures/figure1.png`)
3. Verify the file exists and has non-zero size

### 5. Verify and report

- Confirm the output file exists and has non-zero size
- Report the file path to the user
- If rendering failed, report the error and fall back to the next backend

## Usage Examples

### Example 1 — Render via PaperBanana MCP
```
User: "Generate a framework figure for our attention mechanism"
```
→ Call `generate_diagram` MCP tool with source context and caption
→ Move output to target path

### Example 2 — Render via PaperBanana CLI
```
User: "Render the figure from Publication/paper/figures/figure1_prompt.md"
```
→ Read file → run: `paperbanana generate -i figure1_prompt.md -c "<caption>" -o figure1.png`

### Example 3 — End-to-end with nanobanana-prompt-architect
```
User: "Generate a framework figure for my method and render it"
```
→ First: invoke nanobanana-prompt-architect to produce the SOP prompt
→ Then: render via PaperBanana (preferred) or Gemini CLI nanobanana (fallback)

## Failure Modes & Recovery

| Failure | Recovery |
|---------|----------|
| No API key set | Get free Gemini key from https://aistudio.google.com/app/apikey → `export GOOGLE_API_KEY="key"` |
| PaperBanana not installed | `pip install paperbanana` or use via `uvx` |
| 429 / rate limit | Wait a few minutes and retry; or switch to alternate provider |
| Gemini CLI nanobanana missing | `gemini extensions install https://github.com/gemini-cli-extensions/nanobanana` |
| Low quality output | Increase `--iterations` with PaperBanana (e.g., `--iterations 3`) |
| All backends unavailable | Save prompt to `figure1_prompt.md` with instructions |

## Limits

- Requires network access and a valid API key (Gemini or OpenAI)
- Output is raster (PNG); not suitable when vector graphics (PDF/EPS) are needed
- PaperBanana default model is Gemini; override via `--vlm-provider` / `--image-provider`
- Quality depends on prompt specificity — use nanobanana-prompt-architect for best results
