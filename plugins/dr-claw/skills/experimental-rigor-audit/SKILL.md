---
name: experimental-rigor-audit
description: Audit experiments and writeups for scientific rigor, reasoning transparency, and common pitfalls. Use when reviewing experimental results, designing experiments, or writing research reports.
---

# Experimental Rigor Audit

A checklist-based audit guide for ensuring research experiments and writeups meet top-tier lab standards. Covers hypothesis clarity, experimental design, statistical correctness, reasoning transparency, and honest reporting.

## Part 1: Scientific Virtues (The "Hidden Curriculum")

These are the thinking dispositions top-tier labs look for -- not just whether you can run experiments, but *how you reason about them*. Each virtue includes a guiding principle, a red-flag pattern to avoid, and a writeup bonus pattern.

### 1. Epistemic Humility

- **Principle**: "Too-good-to-be-true results are usually bugs."
- **Red flag**: Celebrating a surprising result without auditing the pipeline first.
- **Bonus pattern**: "Initially, we observed [surprising result]. Suspicious, we audited [specific thing] and found [bug/leak]. After fixing, [corrected result] aligns with expectations."

### 2. Steel-manning the Counter-Argument

- **Principle**: Actively find the strongest attack against your own results.
- **Red flag**: Claiming confirmation without ruling out alternative explanations.
- **Bonus pattern**: "To rule out [alternative explanation], we introduced [control]. The effect persists only in [specific condition], strengthening the [hypothesis]."

### 3. Operationalization of Vague Concepts

- **Principle**: No vague words -- give a mathematical or measurable definition.
- **Red flag**: Using undefined terms like "learning", "understanding", "alignment" without specifying what metric tracks them.
- **Bonus pattern**: "We operationalize [vague concept] as [concrete metric], which provides a continuous measure independent of [confound]."

### 4. Compute Efficiency & Scaling Intuition

- **Principle**: Maximize information gained per unit of compute spent.
- **Red flag**: Brute-force grid search when a few well-chosen points suffice.
- **Bonus pattern**: "Due to compute constraints, we used [proxy metric] as a predictor for [expensive metric]. This allowed sweeping [N] configurations in [short time]."

### 5. Look at the Raw Data

- **Principle**: Don't just stare at aggregate metrics -- inspect individual samples and failure cases.
- **Red flag**: Reporting accuracy without examining *what* the model gets wrong.
- **Bonus pattern**: "Qualitative analysis of failure modes reveals [specific pattern], suggesting [mechanistic insight about why]."

## Part 2: Actionable Checklist (3 Phases)

### A. Experiment Design Phase

- [ ] **Control Group Check**: Does every experiment have a proper baseline/control? (Without one, a number like "80% accuracy" is meaningless.)
- [ ] **Sanity Check**: Feed trivial/degenerate input (zeros, random noise) -- does the model output chance-level? If not, there's a bug.
- [ ] **Metric Definition**: Is the chosen metric appropriate? (e.g., accuracy misleads on imbalanced data; token probability distributions are skewed.)
- [ ] **Operationalize Key Terms**: Every vague concept in the hypothesis has a concrete, measurable definition.
- [ ] **Pre-register Hypothesis**: Write down expected outcome *before* running. "We expect X because Y."
- [ ] **Toy-mode First**: Can the full pipeline be validated on a trivial case before scaling up?
- [ ] **Ablation Design**: Change one variable at a time. If changing two, acknowledge the confound.
- [ ] **Data Leakage Audit**: Is there any overlap between train and evaluation data?
- [ ] **Fair Comparison**: Same compute budget, same data, same tuning effort across conditions.

### B. Results Analysis Phase

- [ ] **Variance Check**: Is the improvement real or within seed noise? Report mean and std across multiple runs.
- [ ] **Cherry-picking Check**: Are you showing the best run or the average? Report honestly: "Best: X%, Mean: Y% +/- Z%."
- [ ] **Causation vs Correlation**: Does the improvement come from the thing you think, or from a side effect? (e.g., adding LayerNorm also changes effective learning rate.)
- [ ] **Effect Size**: Report Cohen's d or equivalent alongside p-values. A statistically significant but tiny effect is not interesting.
- [ ] **Statistical Test Selection**: Parametric vs non-parametric? Paired vs independent? Check normality (Shapiro-Wilk) first.
- [ ] **Error Bars**: Standard deviation (spread) vs standard error (confidence in mean) -- know the difference, report appropriately.
- [ ] **Confidence Intervals**: Use bootstrapped CIs for small sample sizes.
- [ ] **Multiple Comparisons**: Apply Bonferroni correction when testing many hypotheses.
- [ ] **Visualization**: Boxplots + jittered strip plots for distributions. Never bar plots alone.
- [ ] **Inspect Failures**: Print the bad cases. What does the model get wrong? Is there a pattern?

### C. Report Writing Phase

- [ ] **Uncertainty Language**: "These results are consistent with..." not "This proves that..."
- [ ] **Support Type Labels**: Mark claims as: empirical finding / theoretical argument / intuition / speculation.
- [ ] **Limitation Section**: Required. "Toy model results may not transfer to [larger setting]." State scope honestly.
- [ ] **Negative Results**: Report what didn't work. "We attempted X but found it [unstable/unhelpful]. This negative result suggests Y."
- [ ] **Debug Narrative**: Show the process of doubt and verification. "We initially observed Z, suspected [issue], investigated, and found [resolution]."
- [ ] **Alternative Explanations**: Explicitly address the most likely counter-arguments.
- [ ] **Confidence Calibration**: Distinguish strong evidence from weak signals. Don't overstate.

## Critical Red Flags (Stop and Warn)

- Claiming causation from correlation
- No baseline or control condition
- Cherry-picked metrics or runs reported as representative
- Single-run results presented as conclusive (no variance)
- Post-hoc hypothesis presented as pre-registered
- Extraordinary claims without extraordinary evidence
- "Too good to be true" results not audited for bugs/leakage
