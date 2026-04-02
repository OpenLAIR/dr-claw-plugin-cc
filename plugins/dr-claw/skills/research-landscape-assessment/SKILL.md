---
name: research-landscape-assessment
description: >-
  Assess the research landscape for a given topic: quantify hotness/saturation, identify sub-directions,
  find key papers, and track changes over time. Use when the user asks "最近大家在研究XXX的进展如何",
  "XXX方向还热吗", "XXX research landscape", "research progress on XXX", "XXX领域评估",
  or wants a structured assessment of a research field's maturity and trajectory.
user-invocable: true
triggers:
  - 研究进展
  - 进展如何
  - 还热吗
  - 方向评估
  - landscape assessment
  - research landscape
  - field saturation
  - what's the progress on
tools:
  - Bash
  - Read
  - Write
  - Glob
  - Grep
---

# Research Landscape Assessment — Execution Rules

You orchestrate existing tools (trend_scanner.py, search_papers.py) and a helper script
(assess_landscape.py) to produce a structured Chinese-language assessment of any research topic.

## Tool Locations

```
TREND_SCANNER=~/.claude/skills/trending-research-scanner/scripts/trend_scanner.py
SEARCH_LOCAL=~/.claude/cache/trending-research/search_papers.py
ASSESS=~/.claude/skills/research-landscape-assessment/scripts/assess_landscape.py
CACHE=~/.claude/cache/trending-research/assessments
```

---

## Phase 0: PARSE

Extract from the user's question:
1. **Topic** — the research direction (e.g., "RLVR", "Search-R1", "test-time compute scaling")
2. **Time window** — default 6 months; user may specify
3. **Comparison mode** — is the user asking "is it still hot?" (implies diff vs previous snapshot)
4. **Language** — default Chinese output with English paper titles

Derive:
```bash
TOPIC="RLVR"
SLUG=$(echo "$TOPIC" | tr ' ' '-' | tr '[:upper:]' '[:lower:]')
MONTHS=6
TOPIC_DIR=$CACHE/$SLUG
```

Create the topic directory:
```bash
mkdir -p $TOPIC_DIR
```

Check for previous snapshot:
```bash
ls $TOPIC_DIR/snapshot-*.json 2>/dev/null | tail -1
```
If a previous snapshot exists, set DIFF_MODE=true and note the path.

---

## Phase 1: COLLECT — Multi-Source Data Gathering

### Step 1a: Local corpus search
```bash
python3 $SEARCH_LOCAL --query "$TOPIC" --limit 200 --format json > $TOPIC_DIR/collect-local.json
```

### Step 1b: External search via trend_scanner (S2 + OpenAlex + HF + arXiv)
Run these in sequence (API rate limits):
```bash
python3 $TREND_SCANNER search --source s2 --query "$TOPIC" --months $MONTHS --max 80 > $TOPIC_DIR/collect-s2.json
python3 $TREND_SCANNER search --source openalex --query "$TOPIC" --months $MONTHS --max 80 > $TOPIC_DIR/collect-oa.json
python3 $TREND_SCANNER search --source hf --query "$TOPIC" --months $MONTHS --max 50 > $TOPIC_DIR/collect-hf.json
python3 $TREND_SCANNER search --source arxiv --query "$TOPIC" --months $MONTHS --max 80 > $TOPIC_DIR/collect-arxiv.json
```

If the topic has common synonyms or alternative names, run extra queries. Example:
- "Search-R1" → also search "retrieval augmented reasoning", "search augmented LLM"
- "RLVR" → also search "reinforcement learning verifiable rewards"

### Step 1c: Merge and dedupe
```bash
python3 $TREND_SCANNER merge \
    $TOPIC_DIR/collect-s2.json \
    $TOPIC_DIR/collect-oa.json \
    $TOPIC_DIR/collect-hf.json \
    $TOPIC_DIR/collect-arxiv.json \
    --output $TOPIC_DIR/merged.jsonl
```

### Step 1d: Enrich with attention scores
```bash
python3 $TREND_SCANNER enrich $TOPIC_DIR/merged.jsonl \
    --output $TOPIC_DIR/enriched.jsonl --months $MONTHS
```

**Agent checkpoint**: Read enriched.jsonl line count. Target: 30+ papers.
If fewer than 15 papers, broaden the query or extend time window to 12 months.

---

## Phase 2: ASSESS — Run the Assessment Script

```bash
python3 $ASSESS analyze \
    --enriched $TOPIC_DIR/enriched.jsonl \
    --local $TOPIC_DIR/collect-local.json \
    --topic "$TOPIC" \
    --months $MONTHS \
    --output $TOPIC_DIR/snapshot-$(date +%Y-%m-%d).json
```

Read the stdout JSON summary. It reports: total_papers, hotness score, sub_direction count, survey count.

---

## Phase 3: DIFF (conditional — only if previous snapshot exists)

```bash
python3 $ASSESS diff \
    --previous $TOPIC_DIR/snapshot-PREVIOUS.json \
    --current $TOPIC_DIR/snapshot-$(date +%Y-%m-%d).json \
    --output $TOPIC_DIR/diff-$(date +%Y-%m-%d).json
```

Read the diff JSON: new_papers count, citation_growth entries, hotness_delta.

---

## Phase 4: REPORT — Agent Synthesizes Chinese Output

Read the snapshot JSON (and optional diff JSON) and write the final report.
**All prose in Chinese. Paper titles in English. Numbers use Arabic numerals.**

### Report Template

```markdown
# {Topic} 研究全景评估
**评估日期**: {today} | **时间窗口**: 最近{months}个月 | **论文总量**: {total_papers}篇

## 一、热度总览

| 指标 | 数值 | 说明 |
|------|------|------|
| 论文总量 | {total} | 外部{ext}篇 + 本地语料{local}篇 |
| 月均新增 | {avg_per_month} | |
| 增长动量 | {momentum}x | 近3月 vs 前3月 |
| 已有综述 | {survey_count}篇 | |
| 顶会接收 | {conf_total}篇 | {venue breakdown} |
| GitHub复现 | {github_count}个 | 共{stars}星 |
| **综合热度** | **{score}/100** | **{label}** |

热度评分构成:
- 增长动量: {vol}/25
- 头部论文影响力: {impact}/20
- 顶会存在感: {conf}/15
- 社区关注度: {buzz}/15
- 复现活跃度: {repro}/10
- 新鲜度: {fresh}/15

{If DIFF_MODE: ### 与上次评估对比 ({prev_date})
- 论文数变化: {delta}
- 热度变化: {hotness_delta} ({prev_score} → {curr_score})
}

## 二、子方向分析

### 2.{n} {Sub-direction Name (agent assigns Chinese label from top_terms)}
- **状态**: {Emerging/Active/Saturated} (饱和度: {score}/100)
- **论文数**: {count}篇 ({percentage}%)
- **关键词**: {top_terms}
- **代表论文**:
  1. {title} (attention: {score}, citations: {n})
  2. {title}
  3. {title}
- **分析**: {2-3 sentences: what this sub-direction is about, why this saturation level}

{Repeat for each sub-direction, sorted by paper_count descending}

## 三、关键论文

### 高影响力论文 (Top 10 by attention_score)

| # | Title | Score | Citations | Venue | Date |
|---|-------|-------|-----------|-------|------|
{rows}

### 最新论文 (Most Recent 5)

| # | Title | Score | Date | URL |
|---|-------|-------|------|-----|
{rows}

### 综述论文

| # | Title | Citations | Date | URL |
|---|-------|-----------|------|-----|
{rows, or "暂无相关综述" if empty}

## 四、趋势判断

{Agent writes 3-5 paragraphs in Chinese analyzing:}
- 该方向整体处于什么发展阶段 (萌芽/快速增长/成熟/饱和)
- 目前的主要研究瓶颈或开放问题
- 哪些子方向仍有空间、哪些已经非常拥挤
- 如果要进入该方向, 建议关注的具体切入点
- 未来6个月可能的走向

## 五、变化追踪 (仅在Diff模式下显示)

### 新增论文 ({new_count}篇, 按attention_score排序)

| # | Title | Score | Date | Source |
|---|-------|-------|------|--------|
{top 10 new papers}

### 引用增长显著的论文

| # | Title | 上次引用 | 当前引用 | 增长 |
|---|-------|---------|---------|------|
{rows}

### 子方向状态变化

| 子方向 | 上次状态 | 当前状态 | 论文数变化 |
|--------|---------|---------|-----------|
{rows}
```

### Report Writing Guidelines

- Read the abstract and TLDR for each top paper when writing analysis
- Be specific about why a direction is saturated vs emerging — cite evidence
- For sub-direction labels: infer meaning from top_terms and assign concise Chinese names
  (e.g., top_terms ["reward", "math", "verification"] → "数学验证奖励")
- If no previous snapshot exists for diff, skip Section 五 entirely

---

## Quality Checklist

- [ ] At least 3 sources queried successfully (S2, OA, HF, arXiv)
- [ ] Enrichment completed (papers have attention_score)
- [ ] Sub-directions identified (3-6 groups with Chinese labels)
- [ ] Survey papers detected (or explicitly noted as absent)
- [ ] Hotness score computed with component breakdown
- [ ] Report is in Chinese with English paper titles
- [ ] If diff mode: changes are highlighted in Section 五
- [ ] Snapshot saved to assessments/{slug}/ with latest.json symlink

## Failure Modes & Recovery

- **Too few papers (<15)**: Broaden query with synonyms, extend to 12 months, try sub-topic queries
- **API rate limits**: Log which sources failed, proceed with available data, note gaps
- **No surveys found**: State explicitly — this itself is a signal of an emerging field
- **NMF clustering fails**: Script falls back to keyword-frequency grouping automatically
- **No previous snapshot**: Skip diff phase entirely, note this is the first assessment

## Limits

- Provides quantitative assessment, not a deep literature review
- Does not read full paper PDFs
- Sub-direction clustering is approximate (TF-IDF based)
- Hotness score is a heuristic, not ground truth
- Conference detection depends on venue metadata quality
