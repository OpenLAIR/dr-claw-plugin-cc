---
name: searching-local-papers
description: >-
  Search the local corpus of 115K+ AI/ML research papers (79% with abstracts, 84% for 2025+ papers)
  using a precomputed SQLite FTS5 index. Use when the user asks to "search local papers",
  "find papers in my collection", "search my corpus", "search-local", or wants to query their
  locally indexed paper database rather than external APIs.
---

# Searching Local Papers

## Instructions

Search the user's local paper corpus stored at `~/.claude/cache/trending-research/corpus.db`.

### Step 1: Check if index exists

```bash
test -f ~/.claude/cache/trending-research/corpus.db && echo "INDEX_EXISTS" || echo "INDEX_MISSING"
```

If `INDEX_MISSING`, build it first:
```bash
python3 ~/.claude/cache/trending-research/build_index.py \
    --corpus ~/.claude/cache/trending-research/corpus_enriched.jsonl \
    --output ~/.claude/cache/trending-research/corpus.db
```

### Step 2: Run the search

Parse the user's natural language query into appropriate flags:

```bash
python3 ~/.claude/cache/trending-research/search_papers.py \
    --query "<search terms>" \
    [--venue <venue>] \
    [--year <year>] \
    [--year-from <year>] [--year-to <year>] \
    [--source <source>] \
    [--limit <N>] \
    --format json
```

**Parameter mapping from natural language:**
- "CVPR 2024 papers about X" → `--query "X" --venue CVPR --year 2024`
- "recent papers on X" → `--query "X" --year-from 2025`
- "papers from arXiv about X" → `--query "X" --source hf_daily` (arXiv papers come via HF daily)
- "local PDF papers about X" → `--query "X" --source local_pdf`
- "show me 50 results" → `--limit 50`

**Available sources:** `openreview`, `acl`, `hf_daily`, `local_pdf`

**Available venues:** Any venue string (CVPR, ICLR, NeurIPS, ICML, ACL, EMNLP, ECCV, ICCV, NDSS, MLSys, etc.)

### Step 3: Present results

Always use `--format json` to get structured results, then present them as a clean markdown table to the user. Include:
- Paper title (with URL link if available)
- Venue
- Source
- Whether PDF is available locally

If the user wants details about a specific paper, show the full record including abstract, authors, and keywords.

### Corpus Stats (as of 2026-02-27)
- **115,860 papers** indexed
- **91,791 (79.2%) have abstracts**
- **2025+ papers: 34,233 / 40,886 (83.7%) have abstracts**
- Sources: OpenReview (ICLR, NeurIPS, ICML), ACL Anthology, HF Daily Papers, locally scanned PDFs
- Venues covered: ICLR 2021-2026, NeurIPS 2021-2025, ICML 2021-2025, CVPR 2021-2025, ACL 2021-2025, EMNLP 2021-2025, ECCV 2022/2024, ICCV 2021-2025, and more
- Search is BM25-ranked and completes in milliseconds
- For live stats: `python3 ~/.claude/cache/trending-research/search_papers.py --stats`
