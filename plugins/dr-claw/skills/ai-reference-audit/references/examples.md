# Reference Audit Examples

Use these patterns when writing findings.

## Example A: Missing Bib Entries (User-Style)

- Missing bib entries will break compilation:
  - `lora.tex:2` cites `Hu2021LoRA` but only lowercase variants exist in `.bib`.
  - `main.tex:494` cites `hu2022lora` with no matching key in `main.bib`.
  - `main_copy.tex` cites absent keys like `AlphaLLMCPL2024`, `DeepSeekR1`, `KimiK15`, `LogicRL2025`.
- Parsing hazard:
  - Bib entry starts with `@inproceedings { ... }` and malformed spacing/structure causes key parsing failure.

## Example B: Potential Fabrication / High-Risk Metadata

- High-risk entries requiring verification:
  - future-dated references with weak metadata (`2025+`, no DOI/arXiv/URL)
  - nonstandard arXiv IDs or invalid DOI format
  - title/author/year mismatch against trusted indexes
- Report as:
  - `failed verification` when DOI/arXiv/title lookup clearly fails
  - `manual review` when API response is inconclusive

## Example C: RefChecker-Inspired Finding Categories

RefChecker's sample output uses these classes:

- `Error`: author/title/DOI mismatches, incorrect IDs
- `Warning`: year or venue variations
- `Suggestion`: missing link metadata that can be added
- `Unverified`: no reliable source match found

Map these to this skill:

- `Error` -> critical findings
- `Warning` -> metadata formatting risks
- `Unverified` -> potential AI-made-up references (manual verification bucket)
