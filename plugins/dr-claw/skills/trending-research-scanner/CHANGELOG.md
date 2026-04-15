# Changelog

## v1.0.0 — 2026-02-21

### Added
- `trend_scanner.py` CLI with three subcommands: `search`, `enrich`, `merge`
- Four search sources: Semantic Scholar (s2), OpenAlex, Hugging Face Daily Papers (hf), arXiv
- S2 bulk search with citation-count sorting and automatic fallback to regular search
- OpenAlex trending works search with FWCI signal
- HF daily papers multi-week scan with upvote sorting
- arXiv recent papers search sorted by submission date
- Batch enrichment pipeline: S2 citation data, OpenAlex title-match, GitHub stars via `gh api`
- Attention score computation (citation velocity, influential citations, HF upvotes, GitHub stars, conference tier, FWCI)
- Merge/dedupe utility with signal merging across sources
- `SKILL.md` defining iterative agent-in-the-loop protocol with 4 phases: Scope, Search, Enrich, Report
- Report template with themed paper grouping and per-paper summaries
