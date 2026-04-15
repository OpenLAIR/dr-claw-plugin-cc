---
name: trending-research-scanner
description: Iterative field radar — scan trending research papers across Semantic Scholar, OpenAlex, HF Daily Papers, and arXiv with agent-in-the-loop refinement
triggers:
  - scan field
  - research radar
  - trending papers in
  - field briefing for
  - what's hot in
  - field scan
  - trend scan
tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# Trending Research Scanner

You are an iterative research scout. You use `trend_scanner.py` as your search/enrich tool, calling it multiple rounds with different queries and sources. **You** decide when to refine, when to stop, and how to synthesize results.

## Tool Location

```
SCRIPT=scripts/trend_scanner.py (in this skill directory)
```

## Cache Convention

Store intermediate files under:
```
CACHE=.cache/trending-research/{field-slug}/ (project-local cache)
```
Create the directory before first use. Use `scan-{YYYY-MM-DD}` prefix for files.

---

## Phase 1: SCOPE

Before searching, clarify with the user (or infer from context):

1. **Field / topic** — e.g., "LLM reasoning", "protein folding", "multimodal agents"
2. **Time window** — default 3 months; user may want 1, 6, or 12
3. **Depth** — quick scan (5-15 papers) vs. deep dive (30-50+)
4. **Any sub-topics or exclusions** — e.g., "focus on chain-of-thought, skip pure math reasoning"

Set variables:
```
FIELD="LLM reasoning"
MONTHS=3
DEPTH=deep   # quick | normal | deep
SLUG=$(echo "$FIELD" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
```

---

## Phase 2: SEARCH — Multi-Round Iterative

### Round 1: Broad sweep (S2 + OpenAlex)

Run two searches in parallel:
```bash
python3 $SCRIPT search --source s2 --query "$FIELD" --months $MONTHS --max 50 > $CACHE/round1-s2.json
python3 $SCRIPT search --source openalex --query "$FIELD" --months $MONTHS --max 50 > $CACHE/round1-oa.json
```

**Agent checkpoint**: Read both result files. Identify:
- Top-cited papers (sanity check: are they relevant?)
- Emerging sub-themes or clusters
- Gaps — important sub-areas not well represented
- Noise — irrelevant results that suggest query needs refinement

### Round 2: Targeted refinement

Based on Round 1 analysis, run refined queries. Examples:
```bash
# Target a specific sub-theme discovered in Round 1
python3 $SCRIPT search --source s2 --query "chain of thought prompting" --months $MONTHS --max 30 > $CACHE/round2-cot.json
# Try a different angle
python3 $SCRIPT search --source openalex --query "test-time compute scaling" --months $MONTHS --max 30 > $CACHE/round2-ttc.json
```

**Agent checkpoint**: Is coverage sufficient?
- For **quick** depth: 10-15 good papers → proceed to Phase 3
- For **normal** depth: 20-30 good papers → proceed to Phase 3
- For **deep** depth: need 30+ diverse papers → maybe do Round 3

### Round 3+ (optional): Community buzz and very recent

```bash
# HF daily papers for community signal
python3 $SCRIPT search --source hf --query "$FIELD" --months $MONTHS --max 30 > $CACHE/round3-hf.json
# arXiv for very recent preprints
python3 $SCRIPT search --source arxiv --query "$FIELD" --months $MONTHS --max 30 > $CACHE/round3-arxiv.json
```

**Agent decision**: Stop searching when:
- You have enough unique, relevant papers for the requested depth
- Additional queries return mostly duplicates
- Key sub-themes of the field are well represented

### Merge all rounds

```bash
python3 $SCRIPT merge $CACHE/round*.json --output $CACHE/merged.jsonl
```

---

## Phase 3: ENRICH

Batch-enrich the merged set with cross-source signals:

```bash
python3 $SCRIPT enrich $CACHE/merged.jsonl --output $CACHE/enriched.jsonl --months $MONTHS
```

This adds: citation_count, influential_citation_count, cited_by_count, fwci, github_stars, and computes **attention_score** for each paper.

Read the enriched file. The papers are sorted by attention_score descending.

---

## Phase 4: REPORT

Synthesize the enriched papers into a structured Markdown briefing. **You** write this — the script only provides data.

### Report Template

```markdown
# Field Radar: {Field}
**Period**: {date_from} → {today} | **{N} papers** scanned | Top {M} highlighted

## Landscape Summary
{3-5 sentences: what's happening in this field, main trends, notable shifts}

## Theme: {Theme Name}
{1-2 sentence theme description}

### {Paper Title}
- **Score**: {attention_score} | Cit: {citation_count} | Influential: {influential_citation_count} | HF: {hf_upvotes} | GH: {github_stars}★
- **TLDR**: {S2 tldr if available, otherwise write a 1-sentence summary}
- **Why it matters**: {2-3 sentences: motivation, core insight, why this paper is significant}
- **Method**: {1-2 sentences: key technical approach}
- **Key results**: {1-2 sentences: main experimental findings or contributions}
- **Links**: [Paper]({url}) {if github_url: | [Code]({github_url})}

{repeat for each paper in the theme}

## Rising Papers (Fast-Growing Signals)
{Papers published very recently with unusually fast citation/upvote growth}

### {Paper Title}
{same per-paper format as above}

## Cross-Cutting Observations
{2-3 bullet points about field-wide patterns: methodology trends, common benchmarks, open problems}
```

### Per-Paper Summary Guidelines

When writing "Why it matters" and "Method" for each paper:
- Read the abstract and TLDR available in the enriched data
- If the abstract is insufficient, you may fetch the paper URL for more context
- Focus on what's novel and why practitioners should care
- Be specific — avoid generic statements like "this paper advances the field"

### Grouping Heuristic

Group papers into 3-6 themes based on:
- Methodology similarity (e.g., "prompting techniques", "training methods", "evaluation")
- Application domain overlap
- Shared research questions

---

## Attention Score Reference

The `enrich` subcommand computes this score (max ~85):

| Component | Formula | Cap |
|-----------|---------|-----|
| Citation velocity | (citations / months) × 5 | 30 |
| Influential citations | count × 3 | 15 |
| HF upvotes | count × 0.5 | 15 |
| GitHub stars velocity | (stars / months) × 2 | 15 |
| Conference tier | oral/spotlight: 15, poster/major venue: 10 | 15 |
| FWCI | fwci × 2 | 10 |

---

## Error Handling

- If a source times out or returns errors, log it and continue with other sources
- If S2 bulk search fails, the script auto-falls back to regular search
- If enrichment partially fails, the report should note which signals are missing
- Always tell the user how many papers were found vs. how many were enrichable

## Examples

**Quick scan**: "What's hot in multimodal LLMs?"
→ 2 search rounds, 15-20 papers, compact report

**Deep dive**: "Give me a thorough field briefing on reinforcement learning from human feedback"
→ 3-4 search rounds with sub-topic refinement, 40+ papers, detailed themed report

**Focused**: "Trending papers on code generation benchmarks in the last month"
→ 1-2 rounds with tight queries, 1-month window, focused report
