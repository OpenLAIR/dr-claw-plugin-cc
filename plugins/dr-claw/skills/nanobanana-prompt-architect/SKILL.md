---
name: nanobanana-prompt-architect
description: >-
  Generate high-fidelity, math-accurate prompts for academic framework figures
  (ICML/NeurIPS style) and optionally render them end-to-end via Gemini CLI's
  nanobanana extension. Uses a math-first SOP and a PaperBanana-inspired
  workflow (plan -> style -> critic). Use when the user asks for a "technical
  diagram", "schematic", "figure prompt", "academic framework figure",
  "baseline vs proposed method", "TikZ figure", "Mermaid diagram", or
  explicitly mentions "Nanobanana". If the user asks for the SOP location or
  mentions "@SOP_ACADEMIC_FIGURE_PROMPTING", locate and return the SOP path by
  filename search (no hardcoded folder paths).
---

# Nanobanana Prompt Architect - Execution Rules

## Goal & Scope
Handle two request types:
1. Produce a single, well-structured academic figure prompt that is math-first,
   contrastive (baseline vs proposed), and layout-explicit. The output must be a
   single code block containing the prompt and must follow the SOP structure.
2. If the user asks for the SOP location or mentions "@SOP_ACADEMIC_FIGURE_PROMPTING",
   locate and return the SOP file path by filename search (no hardcoded folder paths).

This skill is self-contained and must not depend on hardcoded filesystem paths
to external SOP files.

## Audience & Tone
Researchers and engineers. Precise, technical, and unambiguous language.

## Required Structure / Algorithm
0. Route the request:
   - If the user asks for the SOP path/location or mentions "@SOP_ACADEMIC_FIGURE_PROMPTING",
     follow the SOP path procedure and stop.
   - Otherwise, generate the figure prompt using steps 1-9.

SOP path procedure (decoupled from any specific folder):
   - Target filename: SOP_ACADEMIC_FIGURE_PROMPTING.md
   - Try macOS Spotlight first:
     - mdfind -name SOP_ACADEMIC_FIGURE_PROMPTING.md
   - If mdfind is unavailable or returns no matches, fallback:
     - find ~ -name SOP_ACADEMIC_FIGURE_PROMPTING.md -print
   - If exactly 1 match: reply with the absolute path on a single line only.
   - If multiple matches: reply with one absolute path per line only (no extra text).
   - If no matches: reply with two short sentences max: not found + suggest checking sync/location.

This skill follows a PaperBanana-inspired workflow (Planner -> Stylist -> Critic)
to reduce the common failure mode where "style polishing" accidentally drops
technical details.

1. Inputs (Source Context + Communicative Intent):
   - Source context S: method description and the exact LaTeX symbols/equations.
   - Communicative intent C: the figure caption and what the figure should
     emphasize (overview vs module detail vs pipeline).
   - Optional reference examples: 1-3 exemplar figures (images or textual
     descriptions) that match the desired diagram type/layout.
2. Reference-Driven Scaffold (Retriever Insight):
   - If references are provided, prioritize matching visual structure (diagram
     type/layout) over topical similarity.
   - Extract from references: container shapes, palette, typography, icon style,
     arrow style, spacing density.
   - If no references are provided, assume a clean ICML/NeurIPS look.
3. Context & Symbol Extraction (Content Planning):
   - Identify exact variable names and operators from the paper or user input.
   - List inputs, intermediate variables, parameters, and operations (Top-k,
     sigmoid, EMA update, thresholds).
4. Define Visual Structure (Layout-First):
   - Choose the layout (side-by-side, top-down pipeline, or multi-panel).
   - Specify the flow direction (Left -> Right or Top -> Down).
5. Draft the Prompt (Contrastive Narrative - Planner):
   - Use the SOP template with three sections: Goal & Layout, Panel Details,
     Caption.
   - Enforce baseline vs proposed method contrast unless the user explicitly
     asks for a single method.
6. Math-First Mapping (Diagram Spec):
   - Ensure every visual element maps to a symbol or equation in the prompt.
7. Style Pass (Stylist):
   - Add concrete style constraints (colors, shapes, fonts, line weights,
     rounding, spacing).
   - Default NeurIPS-style options (use if the user does not specify style and
     no references are provided):
     - Background: pure white or very light neutral.
     - "Zone" grouping: large rounded containers with very light pastel fills
       (roughly 10-15% opacity) to group stages.
     - Palette (pick 1 primary + 1 accent; use saturation only for key outputs):
       - Pastel fills: cream (#F5F5DC), pale blue (#E6F3FF), mint (#E0F2F1).
       - Accents: teal, blue, orange, pink (keep medium saturation).
     - Shapes: rounded rectangles for process nodes; dashed borders for optional
       paths/scopes; 3D stacks only when encoding tensor shape is important.
     - Lines: solid for main data flow; dashed for auxiliary/gradients/optional;
       orthogonal elbows for precise architectures; curved arrows for feedback
       loops/high-level narrative flow.
     - Typography: sans-serif for module labels; math variables in serif italic
       consistent with LaTeX ($x_t$, $\theta$, $\mathcal{L}$).
   - Avoid rigid semantic bindings (PaperBanana insight):
     - Do not prescribe "component type -> fixed color/icon" rules.
     - Use color primarily to group logic and emphasize critical elements.
   - Preserve any high-quality style implied by the request; intervene only
     when the description is underspecified, outdated, or visually cluttered.
   - Respect diversity: do not force a single "flat" style if the user clearly
     wants illustrative/3D icons and it remains professional.
8. Critic Pass (Self-Critique + Revision):
   - Sanity-check the prompt against four dimensions:
     - Faithfulness: no hallucinated blocks; correct math and naming.
     - Conciseness: avoid redundant labels/legends; keep text minimal.
     - Readability: clear flow, adequate spacing, consistent typography.
     - Aesthetics: professional palette, consistent line weights, alignment.
   - Explicit checks:
     - Text QA: no typos, consistent variable formatting ($...$), and do not put
       the figure caption text inside the image.
     - Remove redundant "text legend" paragraphs unless the figure truly needs
       a legend.
   - Revise the prompt accordingly. Prefer incremental edits over rewriting
     from scratch.
9. Output Formatting:
   - Output only a single fenced code block labeled `markdown`.
   - Inside the code block, use the SOP blockquote structure.

## Quality Checklist
- [ ] SOP path requests do not use hardcoded folder paths
- [ ] SOP path requests return only path lines (no prose) when matches exist
- [ ] Figure prompt output is a single code block with no extra prose
- [ ] Figure prompt uses the SOP structure: Goal, Layout, Panel Details, Caption
- [ ] Baseline vs proposed method is explicitly contrasted (unless not applicable)
- [ ] Layout and flow direction are specified before panel details
- [ ] Each panel maps visuals to exact LaTeX symbols/equations
- [ ] Key labels call out the flaw/benefit or mechanism
- [ ] Style constraints are concrete (palette, shapes, arrows, typography)
- [ ] Critic pass covered: faithfulness, conciseness, readability, aesthetics
- [ ] Prompt prohibits inserting the caption text inside the image

## Style & Formatting Rules
- If the user asks for the SOP location/path, the response must be path lines only
  (no bullets, no code fences, no extra text).
- Otherwise, the final response must be a single fenced code block labeled `markdown`.
- Inside the code block, use blockquote lines starting with `>`.
- Use bold labels `**Goal:**`, `**Layout:**`, `**Panel X:**`, and `**Caption:**`.
- Use bullet points for panel details.
- Keep the tone technical and precise (no marketing language).

## Failure Modes & Recovery
**Request is vague**
-> Ask 2-3 focused questions: subject, baseline vs proposed, and key equations.

**Layout is unclear**
-> Propose a 2- or 3-panel structure and ask for confirmation.

**No math provided**
-> Ask for the exact LaTeX symbols or provide placeholders (clearly marked).

**No references provided**
-> Proceed zero-shot with a clean ICML/NeurIPS aesthetic and explicit style
   constraints.

**SOP file not found**
-> Report it is not found and suggest checking sync/location.

## Examples

### Example 1
**Prompt ->** "Make a prompt for a 2-panel comparison of CNN vs Transformer for image classification."

**Expected ->** A SOP-formatted code block with two panels labeled CNN and Transformer, mapping visuals to symbols and a concise caption.

### Example 2
**Prompt ->** "Create a technical figure prompt for a data pipeline with three stages: ingest, process, serve."

**Expected ->** A 3-panel SOP-formatted prompt with arrows, stage labels, math labels where applicable, and a concise academic caption.

### Example 3
**Prompt ->** "Write a NeurIPS-style figure prompt using a 2-stage approach: content plan first, then style pass."

**Expected ->** A SOP-formatted code block where style details are clearly
separated from math-first content constraints (and no technical content is
dropped).

### Example 4
**Prompt ->** "where is @SOP_ACADEMIC_FIGURE_PROMPTING?"

**Expected ->** One or more absolute paths to SOP_ACADEMIC_FIGURE_PROMPTING.md, one per line.

## Reference Material
See `references/examples.md` for SOP-aligned examples of high-quality academic figure prompts.

## Step 10 (Optional — End-to-End Rendering)

After generating the SOP prompt (Steps 1–9), optionally render it into an actual image.

**When to trigger**: The user explicitly requests end-to-end generation (e.g., "generate and
render", "create the figure image", "render it too"), or passes a `--render` flag.

**Procedure**:
1. Extract the prompt text from the SOP code block generated in Step 9.
2. Save the prompt to a temporary file (e.g., `figure1_prompt.md`).
3. Render using PaperBanana (preferred) or Gemini CLI nanobanana (fallback):

   **Option A — PaperBanana** (recommended, multi-agent with iterative refinement):
   - Via MCP tool (if `generate_diagram` is available):
     ```
     Call MCP tool: generate_diagram
       source_context: <extracted prompt text>
       caption: <caption from SOP>
       iterations: 3
     ```
   - Via CLI:
     ```bash
     paperbanana generate -i figure1_prompt.md -c "<caption>" -o <target_path>
     ```
   - Repo: https://github.com/llmsresearch/paperbanana.git

   **Option B — Gemini CLI nanobanana** (simpler, single-shot):
   ```bash
   gemini -y -p "Use the generate_image tool to create this image: <extracted_prompt>"
   ```
   Then: `mv ./nanobanana-output/<generated_file>.png <target_path>`

4. Move the generated image to the target directory:
   - Default: `Publication/paper/figures/figure1.png` (InnoFlow projects)
   - Or user-specified path
5. Present both the SOP prompt and the rendered image path to the user.

**Prerequisites** (at least one):
- PaperBanana: `pip install paperbanana` + `GOOGLE_API_KEY` env var
- Gemini CLI + nanobanana extension: `gemini extensions install https://github.com/gemini-cli-extensions/nanobanana` + `GEMINI_API_KEY` env var
- API keys: free from https://aistudio.google.com/app/apikey

**Fallback**: If no rendering backend is available, save the SOP prompt to
`figure1_prompt.md` and inform the user:
> "The SOP prompt has been saved. Install PaperBanana (`pip install paperbanana`)
> or Gemini CLI with nanobanana extension to render it."

## Limits
- Steps 1–9 produce prompts only; image rendering requires Step 10 (opt-in).
- Do not write full paper sections, narratives, or long prose explanations.
- Avoid photorealistic styling or non-technical themes.
