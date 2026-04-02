---
name: searching-ai-papers
description: >-
  Search general-domain AI/ML papers across arXiv, Semantic Scholar, OpenAlex, OpenReview, ICLR accepted
  papers (OpenReview), and Hugging Face Daily Papers without MCP. Use when the user asks to "search arXiv",
  "find ML/AI papers", "openreview", "semantic scholar", "openalex", "Hugging Face daily papers", or wants
  multi-source AI literature mining, hot/trending paper lists, or accepted ICLR paper metadata.
---

# Searching AI Papers — Execution Rules

## Goal & Scope
Provide fast, multi-source discovery of AI/ML papers (arXiv, Semantic Scholar, OpenAlex, OpenReview,
ICLR accepted papers, Hugging Face Daily Papers) with deduped results and a clean summary table or JSON.
This skill is for discovery, not full literature review writing or PDF/LaTeX processing.

## Audience & Tone
Researchers and engineers. Be concise, structured, and explicit about search scope and limits.

## Required Structure / Algorithm
1. Confirm the query and scope:
   - Ask for missing query/topic (unless the user only wants Hugging Face Daily Papers).
   - Ask which sources to include if the user specifies preferences; otherwise default to all.
   - Ask for year range or max results if the user needs it; otherwise use defaults.
2. Run the bundled script to retrieve results:
   - `python3 ~/.codex/skills/searching-ai-papers/scripts/search_ai_papers.py --query "..."`
   - Include `--sources`, `--max-results`, optional year filters or OpenReview group.
   - For accepted ICLR papers, use `--sources iclr_accepted --iclr-year YYYY`.
   - For Hugging Face Daily Papers, use `--hf-date`, `--hf-week`, `--hf-month`, and `--hf-sort`
     (default `trending` for hot papers).
3. Return results in a compact summary:
   - Provide a short count by source and total after dedupe.
   - Provide a markdown table of top results.
   - Offer JSON output if the user wants programmatic processing.
4. If the user asks for full PDFs, LaTeX, clustering, or synthesis:
   - Clarify that this skill only searches and summarizes metadata.
   - Offer to extend the pipeline or switch skills if needed.

## Quality Checklist
- [ ] Query and source scope are clear.
- [ ] Results are deduped by title unless the user opts out.
- [ ] Output includes title, sources, year, score (if available), and URL.
- [ ] Any failures are reported with partial results.

## Style & Formatting Rules
- Default output is a markdown table (includes a Score column for hot/trending lists).
- Keep titles trimmed; list at most 3 authors plus "et al.".
- Use short, plain-language notes; avoid marketing tone.

## Failure Modes & Recovery
- Missing query: ask for the topic or keywords.
- API errors/rate limits: report which sources failed and continue with the rest.
- Too many results: ask for a narrower query or apply a year range.

## Security & Privacy
- Do not request or expose API keys unless the user explicitly wants to configure them.
- Only write output files to user-provided paths.
- Never run destructive shell commands.

## Examples
**Prompt →** "Search arXiv and OpenReview for efficient transformer pruning papers (2022-2025)"
**Expected →** Run the script with `--sources arxiv,openreview --year-from 2022 --year-to 2025` and return a table.

**Prompt →** "Find recent ML systems papers across arXiv, OpenAlex, and Semantic Scholar"
**Expected →** Run with default max results, return a deduped table and counts.

**Prompt →** "Show hot Hugging Face daily papers about diffusion models this week"
**Expected →** Use `--sources hf_daily --hf-week YYYY-Www --hf-sort trending` and filter by query.

**Prompt →** "Get accepted ICLR 2025 papers"
**Expected →** Use `--sources iclr_accepted --iclr-year 2025` and return a table.

## Limits
- This skill does not download PDFs or LaTeX source.
- This skill does not write full literature reviews or do clustering unless the user requests
  a follow-on workflow.
