# Changelog — Writing Experiment Reports Skill

## v1.0 — 2026-01-26

### Initial Release
Created comprehensive skill for generating LaTeX experiment reports.

**Features:**
- Automated WandB data fetching and analysis
- Clean visualization generation (removes empty subplots)
- LaTeX report generation with equations, tables, and figures
- Timestamped folder creation in Overleaf directory
- Supporting files: README, CSV, plain text summary
- Quality validation checklist

**Workflow:**
1. Gather experiment information
2. Fetch and analyze data
3. Create clean visualizations (3-4 panel training dynamics + 4 panel detailed analysis)
4. Generate LaTeX with methodology, results, analysis, conclusion
5. Create supporting files
6. Organize in timestamped folder
7. Validate completeness

**Based on successful workflow from:**
- Citation reward ablation study (Jan 26, 2026)
- Baseline vs citation comparison with 17 test sets
- WandB data integration
- Clean subplot handling after user feedback

**Resources:**
- `resources/report-template.tex` - LaTeX template structure
- `tests/prompts.txt` - 5 test prompts with expected behaviors

### Key Design Decisions
- **Timestamped folders:** Ensures no overwrites, tracks report versions
- **Empty subplot removal:** User feedback showed empty plots are confusing
- **Two-figure approach:** Overview (training dynamics) + detailed analysis (4 panels)
- **CSV inclusion:** Enables further analysis in Excel/Python
- **Plain text summary:** Quick terminal review without LaTeX compilation

### Known Limitations
- Requires actual data (won't hallucinate results)
- LaTeX only (not Word/Markdown)
- Assumes Dropbox/Overleaf integration
- Python dependencies: matplotlib, pandas, numpy, wandb

### Future Enhancements (v1.1+)
- [ ] Support for multiple experiment groups (3+ way comparisons)
- [ ] Automated statistical significance testing
- [ ] Interactive HTML reports alongside LaTeX
- [ ] Template selection (conference-specific formats)
- [ ] Bibtex generation from WandB run notes
