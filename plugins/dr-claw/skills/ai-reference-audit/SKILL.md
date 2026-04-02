---
name: ai-reference-audit
description: Run strong reference audits for AI research papers and repos. Use when asked to check LaTeX/BibTeX citations for missing keys, malformed bibliography entries, formatting defects, or potential AI-made-up references, and when the request is report-only (no content edits).
---

# AI Reference Audit

Run deterministic static checks first, then targeted online verification.

## Quick Start

Run the bundled auditor from the repo root:

```bash
python ~/.claude/skills/ai-reference-audit/scripts/ref_audit.py --repo . --verify-limit 120
```

Emit machine-readable output:

```bash
python ~/.claude/skills/ai-reference-audit/scripts/ref_audit.py --repo . --verify-limit 120 --json
```

Disable network verification when offline:

```bash
python ~/.claude/skills/ai-reference-audit/scripts/ref_audit.py --repo . --no-network
```

## Workflow

1. Discover all LaTeX root files (`\documentclass`) and their reachable `\input`/`\include` graph.
2. Resolve bibliography files from `\bibliography{...}` / `\addbibresource{...}`.
3. Compare cited keys vs parsed `.bib` keys per root paper.
4. Flag BibTeX structure defects:
   - malformed entry starts/terminators
   - duplicate keys
   - missing required metadata (title/author/year/venue)
   - invalid DOI or arXiv formats
5. Mark high-risk potential fabrication using non-Semantic-Scholar checks only:
   - Crossref for DOI
   - arXiv API for arXiv IDs
   - OpenAlex title matching when DOI/arXiv unavailable
6. Report findings only unless explicitly asked to edit files.

## Reporting Rules

- Prioritize findings in this order: missing keys/bib files, malformed entries, metadata defects, potential fabrication.
- Include file and line numbers in every finding.
- Distinguish:
  - `failed verification`: high-risk potential AI-made-up reference
  - `unknown verification`: needs manual review, not a confirmed fabrication
- Ignore Semantic Scholar checks unless explicitly requested.

## References

- Use `references/examples.md` for output style and concrete examples.
