---
name: writing-experiment-reports
description: >-
  Generate comprehensive LaTeX experiment reports for machine learning ablation studies.
  Use when user requests "create report", "generate latex report", "make comprehensive report",
  "overleaf report", "ablation study report", or needs academic documentation of training experiments
  with plots, tables, equations, and analysis. Creates timestamped folder in user's Overleaf Dropbox
  directory with all necessary files.
---

# Writing Experiment Reports — Execution Rules

## Goal & Scope
Generate publication-ready LaTeX reports documenting machine learning experiments with:
- Complete mathematical formulations (equations for models, losses, rewards)
- Clean visualizations showing training dynamics and comparisons
- Detailed tables with quantitative results across test sets
- Full methodology, results, analysis, and conclusion sections
- Hypothesis validation with supporting evidence
- All files organized in timestamped Overleaf-ready folder

## Audience & Tone
Academic researchers, graduate students, and engineers writing papers or technical reports.
Tone: Professional, precise, objective. Use standard academic writing conventions.

## Required Execution Algorithm

### 1. GATHER EXPERIMENT INFORMATION
Ask the user or investigate:
- What is being compared? (baseline vs treatment, ablation variants, model architectures)
- Data source? (WandB URLs, CSV files, checkpoint directories)
- Hypothesis being tested?
- Key metrics? (accuracy, loss, rewards, F1, etc.)
- Number of test sets or evaluation scenarios?
- Model/method names and configurations?

### 2. FETCH AND ANALYZE DATA
**For WandB experiments:**
- Use WandB API to fetch training history for all runs
- Identify available metrics (validation accuracy, KL divergence, losses, etc.)
- Check which metrics have complete data vs missing data
- Calculate summary statistics (mean, std, final values, improvements)

**For file-based data:**
- Read CSV/JSON files with results
- Parse checkpoint directories for available models
- Extract relevant metrics and organize by test set

**Critical validation:**
- Verify all baseline and treatment runs have matching test sets
- Calculate deltas (treatment - baseline) for each metric
- Count improvements, degradations, and equal performance

### 3. CREATE CLEAN VISUALIZATIONS
**Figure 1: Training Dynamics (3-4 panels)**
- Panel 1 (top/full width): Main metric over iterations (e.g., average validation accuracy)
  - Both baseline and treatment curves
  - Final value annotations with horizontal dashed lines
  - Clear legend
- Panel 2 (bottom-left): Secondary metric (e.g., KL divergence, loss)
  - Mean value annotation if stable
- Panel 3 (bottom-right): Test set comparison (bar chart)
  - Show subset of representative test sets (top 10-12)
  - Add improvement labels (+0.33, +0.25, etc.) for significant gains

**Figure 2: Detailed Analysis (4 panels)**
- Panel 1: Main metric curves over full training
- Panel 2: Top improvements (horizontal bar chart with color gradient)
- Panel 3: Distribution histogram (baseline vs treatment)
  - Add mean lines with values
- Panel 4: Scatter plot (baseline x-axis, treatment y-axis)
  - y=x diagonal line
  - Annotation: "X improved, Y degraded"

**Critical rules:**
- **Remove empty subplots** - only show metrics with available data
- Use consistent colors (blue for baseline, orange for treatment)
- High DPI (150) for publication quality
- Save as PNG with descriptive names (e.g., `experiment_comparison.png`, `experiment_key_metrics.png`)
- Add grid with alpha=0.3 for readability

### 4. GENERATE LATEX REPORT
Use the structure from `resources/report-template.tex`:

**Required sections:**
1. **Title** - Descriptive with method names
2. **Abstract** - 1 paragraph summary of hypothesis, method, key result
3. **Introduction** - Motivation and hypothesis
4. **Methodology**
   - Model architecture (with equation if applicable)
   - Training procedure (GRPO, SGD, etc.)
   - Reward/loss formulation (with numbered equations)
   - Hardware and hyperparameters (in table)
   - Dataset description
5. **Results**
   - Training dynamics (reference Figure 1)
   - Detailed comparison table (all test sets with baseline, treatment, delta)
   - Summary statistics table (averages, counts of improved/degraded)
   - Key findings as bullet points
6. **Analysis**
   - Interpret the results
   - Explain why treatment worked or didn't
   - Address hypothesis
7. **Conclusion**
   - State whether hypothesis is confirmed/rejected
   - Implications for future work
8. **Appendix** (if needed)
   - Full hyperparameter list
   - Additional test set details

**Mathematical notation:**
- Use `\texttt{}` for code/variable names
- Use `\mathcal{}` for distributions, `\mathbb{}` for sets
- Number all key equations
- Define all symbols in table or inline

### 5. CREATE SUPPORTING FILES
**README.md:**
```markdown
# [Experiment Name] Report

**Generated:** [timestamp]
**Version:** [Final/Draft]

## Contents
- main.tex - Comprehensive LaTeX report
- [experiment]_comparison.png - Training dynamics
- [experiment]_key_metrics.png - Detailed analysis
- [experiment]_detailed.csv - Raw comparison data
- [experiment]_summary.txt - Quick summary

## How to Use
### Compile LaTeX Report
pdflatex main.tex
pdflatex main.tex  # Run twice for references

Or upload to Overleaf:
1. Upload main.tex and PNG files
2. Click "Recompile"

## Key Findings
- [Bullet point summary of results]
```

**[experiment]_summary.txt:**
- Plain text summary with ASCII tables
- Key statistics (improvements, degradations, averages)
- Suitable for quick review in terminal

**[experiment]_detailed.csv:**
- Columns: Test Set, Baseline Metric, Treatment Metric, Delta, Improvement %
- All test sets included
- Sortable for further analysis

### 6. ORGANIZE IN TIMESTAMPED FOLDER
**Default location:** `/Users/yixinliu/Lehigh University Dropbox/Liu Yixin/应用/Overleaf/`

**Folder naming:** `[experiment-name]-report-YYYYMMDD_HHMMSS`
Example: `citation-reward-ablation-20260126_082436`

**File structure:**
```
experiment-report-YYYYMMDD_HHMMSS/
├── main.tex                         # Main report
├── experiment_comparison.png        # Figure 1
├── experiment_key_metrics.png       # Figure 2
├── experiment_detailed.csv          # Raw data
├── experiment_summary.txt           # Quick summary
├── README.md                        # Usage guide
├── STRUCTURE.md                     # Document structure explanation
└── build.sh                         # Compilation script
```

### 7. FINAL VALIDATION CHECKLIST
Before delivery:
- [ ] All equations are numbered and referenced in text
- [ ] All figures are referenced in text with "Figure X shows..."
- [ ] All tables have captions and are referenced
- [ ] No empty subplots in visualizations
- [ ] Final metric values match between text, tables, and plots
- [ ] Hypothesis statement is clear and conclusion addresses it
- [ ] File names are descriptive and consistent
- [ ] README includes compilation instructions
- [ ] Timestamp is in folder name
- [ ] All files are in Overleaf directory

## Quality Checklist

**Report Quality:**
- [ ] Abstract is self-contained (hypothesis + result in 1 paragraph)
- [ ] Mathematical formulations are complete and correct
- [ ] All metrics defined before use
- [ ] Results section is objective (no interpretation)
- [ ] Analysis section interprets results (with reasoning)
- [ ] Conclusion explicitly states confirmed/rejected hypothesis
- [ ] References to figures/tables use \ref{} properly

**Visualization Quality:**
- [ ] No empty or broken subplots
- [ ] Legend is clear and not obstructing data
- [ ] Axes labeled with units if applicable
- [ ] Font sizes are readable (10-12pt)
- [ ] Colors are distinguishable and consistent
- [ ] Annotations (improvement labels) are legible
- [ ] DPI ≥ 150 for publication quality

**Data Quality:**
- [ ] All test sets accounted for
- [ ] Delta calculations verified (treatment - baseline)
- [ ] No missing data in critical comparisons
- [ ] Summary statistics match detailed data
- [ ] Improvement/degradation counts are correct

## Style & Formatting Rules

**LaTeX formatting:**
- Use `\section{}`, `\subsection{}` for structure
- Use `\textbf{}` for emphasis (sparingly)
- Use `booktabs` package for professional tables: `\toprule`, `\midrule`, `\bottomrule`
- Use `graphicx` with `[width=\textwidth]` for figures
- Use `amsmath` for equations with `\begin{equation}...\end{equation}`
- Use `\label{}` and `\ref{}` for cross-references

**Visualization formatting:**
- Figure size: (15-16, 10-11) inches for multi-panel
- Line width: 2.5-3.0 for main curves
- Alpha: 0.7-0.9 for overlapping elements
- Font size: 11-13 for titles, 10-12 for labels, 9-10 for annotations
- Grid: alpha=0.3, always on for readability
- Colors: Use colorblind-friendly palettes (default matplotlib colors work)

**Numerical formatting:**
- Accuracy/scores: 4 decimal places (0.7420)
- Percentages: 1-2 decimal places (7.51%, 82.4%)
- Large numbers: Use comma separators (1,234,567)
- Very small numbers: Scientific notation (1.23e-4)
- Improvement deltas: Sign prefix (+0.333, -0.012, or space for ~0)

## Failure Modes & Recovery

**Missing data for some metrics:**
→ Create visualizations with only available data. Remove empty subplots entirely. Document in README which metrics were unavailable.

**Inconsistent test set names:**
→ Standardize naming (remove prefixes, truncate long names). Create mapping table in appendix.

**Training runs have different iteration counts:**
→ Use final available values for each run. Note discrepancy in methodology section with reason.

**No clear hypothesis stated by user:**
→ Infer from experiment design. Ask: "I understand you're comparing X vs Y. Is the hypothesis that X will improve [metric] due to [reason]?"

**Very large number of test sets (>20):**
→ Create summary table with averages and highlights. Include full detailed table in appendix. Visualizations show top 10-12 most representative/improved.

**User requests changes after initial generation:**
→ Regenerate specific components (plots, tables, or sections) and update existing files. Don't recreate entire folder unless necessary.

## Examples

### Example 1: Citation Reward Ablation
**Prompt →** "Create comprehensive report on citation reward ablation comparing baseline vs citation, use WandB data"

**Expected workflow:**
1. Fetch WandB data for both runs (baseline: udm1u2ap, citation: 88lhl157)
2. Create 2 figures:
   - Training dynamics (validation accuracy, KL divergence, test set bars)
   - Detailed metrics (curves, improvements, distribution, scatter)
3. Generate LaTeX with:
   - Composite reward equation: R = 0.5×R_outcome + 0.2×R_format + 0.2×R_cite + 0.1×R_consistency
   - Table: 17 test sets with accuracies and deltas
   - Result: 14 improved, 0 degraded
4. Create folder: `citation-reward-ablation-20260126_082436/`
5. Include: main.tex, 2 PNGs, CSV, summary.txt, README.md

**Key finding:** Citation reward improved average accuracy by 7.51% with no degradation. Hypothesis confirmed.

### Example 2: LLM vs Simple Baselines
**Prompt →** "Make report comparing reasoning LLM vs CNN/SVM/fuzzy models on audio deepfake detection"

**Expected workflow:**
1. Gather results for all models (LLM, CNN, SVM, fuzzy)
2. Create comparison figures:
   - Bar chart: accuracy by model and test set
   - Training curves (if available for neural models)
   - Confusion matrices for each model
3. Generate LaTeX with:
   - Model descriptions (LLM architecture, CNN layers, SVM kernel, fuzzy rules)
   - Comparison table: accuracy, F1, inference time, model size
   - Analysis: Does LLM's reasoning justify complexity?
4. Hypothesis validation: "LLM achieves better generalization due to reasoning" - test across distribution shifts

### Example 3: Hyperparameter Sweep
**Prompt →** "Create report for learning rate sweep results, 5 different LRs tested"

**Expected workflow:**
1. Load results for lr=[1e-5, 5e-5, 1e-4, 5e-4, 1e-3]
2. Create figures:
   - Line plot: validation accuracy vs iteration for each LR (5 curves)
   - Heatmap: final accuracy vs LR
   - Convergence speed comparison
3. LaTeX report:
   - Table: LR, final accuracy, iterations to convergence, stability
   - Analysis: optimal LR balances speed and stability
   - Recommendation: lr=5e-5 for this architecture/dataset

## Limits
- This skill creates **experiment reports**, not general documentation or papers
- Focus is on **comparing methods/models** with quantitative results
- Not for: literature reviews, theoretical derivations without experiments, tutorials
- Requires concrete experimental results (cannot generate fake data)
- LaTeX only (not Word, Markdown long-form, or HTML reports)
- Assumes user has Overleaf directory in Dropbox (or will specify alternative)

## Safety & Best Practices
- **Verify data sources** before fetching (check WandB URLs, file paths exist)
- **Do not hallucinate results** - all numbers must come from actual data
- **Preserve reproducibility** - include WandB links, git commits, hyperparameters
- **Handle missing data gracefully** - document what's unavailable, don't fill gaps
- **Ask before overwriting** - if report folder already exists, confirm with user
- **Respect file sizes** - if CSV >100MB, summarize instead of including full data
- **Validate calculations** - double-check deltas, percentages, and aggregate statistics

## Technical Dependencies
This skill assumes:
- Python 3.8+ with matplotlib, pandas, numpy
- WandB API access (if using WandB data)
- LaTeX distribution (user-side for compilation)
- Dropbox sync for Overleaf directory

If dependencies missing, document in README with installation instructions.
