#!/usr/bin/env python3
"""assess_landscape.py — Compute research landscape metrics from enriched papers.

Two subcommands:
  analyze  — Build a snapshot with hotness score, sub-directions, survey detection
  diff     — Compare two snapshots and output structured delta
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ──────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────

SURVEY_KEYWORDS = [
    "survey", "review", "overview", "systematic review",
    "tutorial", "comprehensive study", "literature review",
    "position paper", "landscape", "taxonomy", "benchmark survey",
]

TOP_VENUES = [
    "neurips", "nips", "icml", "iclr", "aaai", "ijcai",
    "acl", "emnlp", "naacl", "cvpr", "eccv", "iccv",
    "sigir", "kdd", "www", "icde", "vldb",
]


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower()).strip()


# ──────────────────────────────────────────────
# Data Loading
# ──────────────────────────────────────────────


def load_papers(enriched_path: str, local_path: Optional[str] = None) -> List[Dict]:
    """Load enriched JSONL and optionally merge local corpus results."""
    papers: List[Dict] = []

    with open(enriched_path) as f:
        for line in f:
            line = line.strip()
            if line:
                papers.append(json.loads(line))

    if local_path and os.path.exists(local_path):
        try:
            raw = json.loads(Path(local_path).read_text())
            local_papers = raw.get("results", raw) if isinstance(raw, dict) else raw
            if not isinstance(local_papers, list):
                local_papers = []
        except Exception:
            local_papers = []

        existing = {normalize_title(p.get("title", "")) for p in papers}
        for lp in local_papers:
            key = normalize_title(lp.get("title", ""))
            if key and key not in existing:
                lp.setdefault("source", "local_corpus")
                papers.append(lp)
                existing.add(key)

    return papers


# ──────────────────────────────────────────────
# Date helpers
# ──────────────────────────────────────────────


def _parse_date(paper: Dict) -> Optional[dt.date]:
    pub = paper.get("published") or paper.get("date") or ""
    if not pub or len(pub) < 10:
        return None
    try:
        return dt.date.fromisoformat(pub[:10])
    except Exception:
        return None


def _is_within_months(paper: Dict, months: int) -> bool:
    d = _parse_date(paper)
    if not d:
        return False
    return d >= dt.date.today() - dt.timedelta(days=months * 30)


def _is_between_months(paper: Dict, start_months: int, end_months: int) -> bool:
    d = _parse_date(paper)
    if not d:
        return False
    today = dt.date.today()
    return (today - dt.timedelta(days=end_months * 30)) <= d < (today - dt.timedelta(days=start_months * 30))


# ──────────────────────────────────────────────
# Temporal Analysis
# ──────────────────────────────────────────────


def compute_temporal_stats(papers: List[Dict], months: int) -> Dict:
    year_counts: collections.Counter = collections.Counter()
    month_counts: collections.Counter = collections.Counter()

    for p in papers:
        pub = p.get("published") or p.get("date") or ""
        year = p.get("year")
        if pub and len(pub) >= 7:
            month_counts[pub[:7]] += 1
        if pub and len(pub) >= 4:
            try:
                year_counts[int(pub[:4])] += 1
            except ValueError:
                pass
        elif year:
            try:
                year_counts[int(year)] += 1
            except (ValueError, TypeError):
                pass

    recent_3mo = sum(1 for p in papers if _is_within_months(p, 3))
    prev_3mo = sum(1 for p in papers if _is_between_months(p, 3, 6))
    momentum = recent_3mo / max(prev_3mo, 1)

    return {
        "by_year": dict(sorted(year_counts.items())),
        "by_month": dict(sorted(month_counts.items())),
        "total": len(papers),
        "recent_3mo": recent_3mo,
        "prev_3mo": prev_3mo,
        "momentum": round(momentum, 2),
        "avg_per_month": round(len(papers) / max(months, 1), 1),
    }


# ──────────────────────────────────────────────
# Survey Detection
# ──────────────────────────────────────────────


def detect_surveys(papers: List[Dict]) -> List[Dict]:
    surveys = []
    for p in papers:
        title_lower = (p.get("title") or "").lower()
        abstract_lower = (p.get("abstract") or "").lower()
        title_match = any(kw in title_lower for kw in SURVEY_KEYWORDS)
        first_sentence = abstract_lower.split(".")[0] if abstract_lower else ""
        abstract_match = any(kw in first_sentence for kw in ["survey", "review", "overview"])
        if title_match or abstract_match:
            surveys.append(p)
    return surveys


# ──────────────────────────────────────────────
# Conference & GitHub Counting
# ──────────────────────────────────────────────


def count_conference_papers(papers: List[Dict]) -> Dict:
    conf_counts: collections.Counter = collections.Counter()
    for p in papers:
        venue = (p.get("venue") or "").lower()
        for v in TOP_VENUES:
            if v in venue:
                conf_counts[v.upper()] += 1
                break
    return {
        "by_venue": dict(conf_counts.most_common()),
        "total": sum(conf_counts.values()),
    }


def count_github_repos(papers: List[Dict]) -> Dict:
    repos = []
    for p in papers:
        gh_url = p.get("github_url") or ""
        gh_stars = p.get("github_stars") or 0
        if gh_url or gh_stars:
            repos.append({
                "title": p.get("title", ""),
                "github_url": gh_url,
                "stars": gh_stars,
            })
    return {
        "count": len(repos),
        "total_stars": sum(r["stars"] for r in repos),
        "repos": sorted(repos, key=lambda r: r["stars"], reverse=True)[:10],
    }


# ──────────────────────────────────────────────
# Sub-Direction Clustering
# ──────────────────────────────────────────────


def cluster_sub_directions(papers: List[Dict], n_clusters: int = 5) -> List[Dict]:
    """Cluster papers into sub-directions using TF-IDF + NMF.
    Falls back to keyword grouping if sklearn unavailable or too few papers."""
    texts = []
    valid_papers = []
    for p in papers:
        text = f"{p.get('title', '')} {p.get('abstract', '')}"
        if len(text.strip()) > 20:
            texts.append(text)
            valid_papers.append(p)

    if len(texts) < max(n_clusters * 2, 10):
        return _fallback_keyword_clustering(valid_papers)

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.decomposition import NMF
    except ImportError:
        return _fallback_keyword_clustering(valid_papers)

    n = max(3, min(6, len(texts) // 10))

    vectorizer = TfidfVectorizer(
        max_features=2000,
        stop_words="english",
        ngram_range=(1, 2),
        min_df=2,
        max_df=0.8,
    )
    tfidf = vectorizer.fit_transform(texts)
    nmf = NMF(n_components=n, random_state=42, max_iter=300)
    W = nmf.fit_transform(tfidf)
    H = nmf.components_
    feature_names = vectorizer.get_feature_names_out()

    clusters = []
    for topic_idx in range(n):
        top_indices = H[topic_idx].argsort()[-8:][::-1]
        top_terms = [feature_names[i] for i in top_indices]

        assigned = [i for i in range(len(texts)) if W[i].argmax() == topic_idx]
        assigned_papers = [valid_papers[i] for i in assigned]
        assigned_papers.sort(key=lambda p: p.get("attention_score", 0), reverse=True)

        clusters.append({
            "cluster_id": topic_idx,
            "top_terms": top_terms,
            "label": "",  # Agent fills with Chinese label
            "paper_count": len(assigned_papers),
            "papers": [_paper_summary(p) for p in assigned_papers],
            "top_papers": [_paper_summary(p) for p in assigned_papers[:3]],
            "saturation": _compute_saturation(assigned_papers),
        })

    clusters.sort(key=lambda c: c["paper_count"], reverse=True)
    return clusters


def _fallback_keyword_clustering(papers: List[Dict]) -> List[Dict]:
    """Simple bigram-frequency grouping."""
    bigram_counter: collections.Counter = collections.Counter()
    for p in papers:
        words = re.findall(r"[a-zA-Z]{3,}", (p.get("title") or "").lower())
        for i in range(len(words) - 1):
            bigram_counter[(words[i], words[i + 1])] += 1

    clusters = []
    assigned: set = set()

    for (w1, w2), _ in bigram_counter.most_common(5):
        cluster_papers = []
        for i, p in enumerate(papers):
            if i in assigned:
                continue
            title_lower = (p.get("title") or "").lower()
            if w1 in title_lower or w2 in title_lower:
                cluster_papers.append(p)
                assigned.add(i)
        if cluster_papers:
            cluster_papers.sort(key=lambda p: p.get("attention_score", 0), reverse=True)
            clusters.append({
                "cluster_id": len(clusters),
                "top_terms": [w1, w2],
                "label": "",
                "paper_count": len(cluster_papers),
                "papers": [_paper_summary(p) for p in cluster_papers],
                "top_papers": [_paper_summary(p) for p in cluster_papers[:3]],
                "saturation": _compute_saturation(cluster_papers),
            })

    remaining = [papers[i] for i in range(len(papers)) if i not in assigned]
    if remaining:
        remaining.sort(key=lambda p: p.get("attention_score", 0), reverse=True)
        clusters.append({
            "cluster_id": len(clusters),
            "top_terms": ["other"],
            "label": "Other",
            "paper_count": len(remaining),
            "papers": [_paper_summary(p) for p in remaining],
            "top_papers": [_paper_summary(p) for p in remaining[:3]],
            "saturation": _compute_saturation(remaining),
        })

    clusters.sort(key=lambda c: c["paper_count"], reverse=True)
    return clusters


# ──────────────────────────────────────────────
# Saturation Scoring (Per Sub-Direction)
# ──────────────────────────────────────────────


def _compute_saturation(papers: List[Dict]) -> Dict:
    """0-100 saturation: 0-30 Emerging, 31-60 Active, 61-100 Saturated."""
    if not papers:
        return {"score": 0, "label": "Emerging", "components": {}}

    n = len(papers)

    # Survey presence (0 or 30)
    survey_score = 30 if any(
        any(kw in (p.get("title") or "").lower() for kw in SURVEY_KEYWORDS)
        for p in papers
    ) else 0

    # Volume (0-30)
    if n >= 30:
        volume_score = 30
    elif n >= 15:
        volume_score = 20
    elif n >= 5:
        volume_score = 10
    else:
        volume_score = 0

    # Novelty decay (0-20): high if most papers are NOT recent
    recent_ratio = sum(1 for p in papers if _is_within_months(p, 2)) / max(n, 1)
    novelty_score = int(20 * (1 - recent_ratio))

    # Citation concentration (0-20)
    citations = sorted(
        [p.get("citation_count", 0) or p.get("cited_by_count", 0) or 0 for p in papers],
        reverse=True,
    )
    total_cit = sum(citations)
    top3_cit = sum(citations[:3])
    concentration = top3_cit / max(total_cit, 1)
    concentration_score = int(20 * concentration)

    total = min(survey_score + volume_score + novelty_score + concentration_score, 100)

    if total <= 30:
        label = "Emerging"
    elif total <= 60:
        label = "Active"
    else:
        label = "Saturated"

    return {
        "score": total,
        "label": label,
        "components": {
            "survey_presence": survey_score,
            "volume": volume_score,
            "novelty_decay": novelty_score,
            "citation_concentration": concentration_score,
        },
    }


# ──────────────────────────────────────────────
# Hotness Score (Overall)
# ──────────────────────────────────────────────


def compute_hotness_score(
    temporal: Dict,
    conferences: Dict,
    github: Dict,
    papers: List[Dict],
    surveys: List[Dict],
) -> Dict:
    """0-100 overall hotness score."""
    # Volume momentum (max 25)
    momentum = temporal.get("momentum", 1.0)
    vol_score = min(momentum * 20, 25)

    # Top-paper impact (max 20)
    top_papers = sorted(papers, key=lambda p: p.get("attention_score", 0), reverse=True)[:10]
    avg_attn = sum(p.get("attention_score", 0) for p in top_papers) / max(len(top_papers), 1)
    impact_score = min(avg_attn * 0.5, 20)

    # Conference presence (max 15)
    conf_count = conferences.get("total", 0)
    conf_score = min(conf_count * 2, 15)

    # Community buzz (max 15)
    total_upvotes = sum(p.get("hf_upvotes", 0) or 0 for p in papers)
    buzz_score = min(total_upvotes * 0.1, 15)

    # Reproduction (max 10)
    repo_count = github.get("count", 0)
    repro_score = min(repo_count * 3, 10)

    # Freshness (max 15) — inverse of survey saturation
    total = temporal.get("total", 1)
    survey_ratio = len(surveys) / max(total * 0.1, 1)
    freshness_score = max(0, min(15, 15 * (1 - survey_ratio)))

    total_score = min(
        round(vol_score + impact_score + conf_score + buzz_score + repro_score + freshness_score, 1),
        100,
    )

    if total_score >= 80:
        label = "火热 (Very Hot)"
    elif total_score >= 60:
        label = "活跃 (Active)"
    elif total_score >= 40:
        label = "稳定 (Steady)"
    elif total_score >= 20:
        label = "降温 (Cooling)"
    else:
        label = "冷门 (Niche)"

    return {
        "score": total_score,
        "label": label,
        "components": {
            "volume_momentum": round(vol_score, 1),
            "top_paper_impact": round(impact_score, 1),
            "conference_presence": round(conf_score, 1),
            "community_buzz": round(buzz_score, 1),
            "reproduction": round(repro_score, 1),
            "freshness": round(freshness_score, 1),
        },
    }


# ──────────────────────────────────────────────
# Paper Summary Helper
# ──────────────────────────────────────────────


def _paper_summary(p: Dict) -> Dict:
    return {
        "title": p.get("title", ""),
        "authors": (p.get("authors") or [])[:3],
        "published": p.get("published") or p.get("date", ""),
        "venue": p.get("venue", ""),
        "url": p.get("url", ""),
        "citation_count": p.get("citation_count", 0) or p.get("cited_by_count", 0) or 0,
        "attention_score": p.get("attention_score", 0),
        "hf_upvotes": p.get("hf_upvotes", 0) or 0,
        "github_stars": p.get("github_stars", 0) or 0,
        "github_url": p.get("github_url", ""),
        "is_survey": any(kw in (p.get("title") or "").lower() for kw in SURVEY_KEYWORDS),
        "arxiv_id": p.get("arxiv_id", ""),
        "source": p.get("source", ""),
    }


# ──────────────────────────────────────────────
# cmd_analyze
# ──────────────────────────────────────────────


def cmd_analyze(args) -> int:
    papers = load_papers(args.enriched, getattr(args, "local", None))
    if not papers:
        print(json.dumps({"error": "No papers found"}))
        return 1

    temporal = compute_temporal_stats(papers, args.months)
    surveys = detect_surveys(papers)
    conferences = count_conference_papers(papers)
    github = count_github_repos(papers)
    clusters = cluster_sub_directions(papers)
    hotness = compute_hotness_score(temporal, conferences, github, papers, surveys)

    top_by_score = sorted(papers, key=lambda p: p.get("attention_score", 0), reverse=True)[:10]
    top_recent = sorted(
        [p for p in papers if p.get("published") or p.get("date")],
        key=lambda p: p.get("published") or p.get("date", ""),
        reverse=True,
    )[:5]

    snapshot = {
        "topic": args.topic,
        "date": dt.date.today().isoformat(),
        "months": args.months,
        "temporal": temporal,
        "hotness": hotness,
        "surveys": [_paper_summary(s) for s in surveys],
        "conferences": conferences,
        "github": github,
        "sub_directions": clusters,
        "top_by_influence": [_paper_summary(p) for p in top_by_score],
        "top_recent": [_paper_summary(p) for p in top_recent],
        "all_papers": [_paper_summary(p) for p in papers],
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))

    # Update latest.json symlink
    latest = output_path.parent / "latest.json"
    if latest.is_symlink() or latest.exists():
        latest.unlink()
    latest.symlink_to(output_path.name)

    print(json.dumps({
        "status": "ok",
        "total_papers": len(papers),
        "hotness": hotness["score"],
        "label": hotness["label"],
        "sub_directions": len(clusters),
        "surveys": len(surveys),
        "snapshot": str(output_path),
    }, ensure_ascii=False))
    return 0


# ──────────────────────────────────────────────
# Diff Computation
# ──────────────────────────────────────────────


def compute_diff(prev: Dict, curr: Dict) -> Dict:
    """Compare two snapshots and produce structured delta."""
    prev_titles: Dict[str, Dict] = {}
    for p in prev.get("all_papers", []):
        key = normalize_title(p.get("title", ""))
        if key:
            prev_titles[key] = p

    # New papers
    new_papers = []
    for p in curr.get("all_papers", []):
        key = normalize_title(p.get("title", ""))
        if key and key not in prev_titles:
            new_papers.append(p)

    # Citation growth
    citation_growth = []
    for p in curr.get("all_papers", []):
        key = normalize_title(p.get("title", ""))
        if key and key in prev_titles:
            prev_cit = prev_titles[key].get("citation_count", 0) or 0
            curr_cit = p.get("citation_count", 0) or 0
            delta = curr_cit - prev_cit
            if delta >= 5:
                citation_growth.append({
                    **p,
                    "citation_delta": delta,
                    "prev_citation_count": prev_cit,
                })
    citation_growth.sort(key=lambda x: x["citation_delta"], reverse=True)

    # Hotness delta
    prev_hotness = prev.get("hotness", {}).get("score", 0)
    curr_hotness = curr.get("hotness", {}).get("score", 0)

    # Sub-direction changes (match by top_terms Jaccard similarity)
    prev_dirs = {i: d for i, d in enumerate(prev.get("sub_directions", []))}
    curr_dirs = curr.get("sub_directions", [])

    direction_changes = []
    for curr_dir in curr_dirs:
        curr_terms = set(curr_dir.get("top_terms", []))
        best_match = None
        best_overlap = 0.0
        for _, prev_dir in prev_dirs.items():
            prev_terms = set(prev_dir.get("top_terms", []))
            union = curr_terms | prev_terms
            if not union:
                continue
            overlap = len(curr_terms & prev_terms) / len(union)
            if overlap > best_overlap:
                best_overlap = overlap
                best_match = prev_dir

        curr_label = curr_dir.get("label") or ", ".join(curr_dir.get("top_terms", [])[:3])
        if best_match and best_overlap > 0.3:
            prev_sat = best_match.get("saturation", {}).get("label", "Unknown")
            curr_sat = curr_dir.get("saturation", {}).get("label", "Unknown")
            if prev_sat != curr_sat:
                direction_changes.append({
                    "direction": curr_label,
                    "prev_status": prev_sat,
                    "curr_status": curr_sat,
                    "paper_count_delta": curr_dir["paper_count"] - best_match.get("paper_count", 0),
                })
        else:
            direction_changes.append({
                "direction": curr_label,
                "prev_status": "N/A (new)",
                "curr_status": curr_dir.get("saturation", {}).get("label", "Unknown"),
                "paper_count_delta": curr_dir["paper_count"],
                "is_new": True,
            })

    # New surveys
    new_surveys = [
        s for s in curr.get("surveys", [])
        if normalize_title(s.get("title", "")) not in prev_titles
    ]

    return {
        "prev_date": prev.get("date"),
        "curr_date": curr.get("date"),
        "paper_count_delta": curr.get("temporal", {}).get("total", 0) - prev.get("temporal", {}).get("total", 0),
        "hotness_delta": round(curr_hotness - prev_hotness, 1),
        "prev_hotness": prev_hotness,
        "curr_hotness": curr_hotness,
        "new_papers": sorted(new_papers, key=lambda p: p.get("attention_score", 0), reverse=True),
        "citation_growth": citation_growth[:20],
        "direction_changes": direction_changes,
        "new_surveys": new_surveys,
    }


def cmd_diff(args) -> int:
    prev = json.loads(Path(args.previous).read_text())
    curr = json.loads(Path(args.current).read_text())

    diff = compute_diff(prev, curr)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(diff, indent=2, ensure_ascii=False))

    print(json.dumps({
        "status": "ok",
        "new_papers": len(diff.get("new_papers", [])),
        "citation_growth": len(diff.get("citation_growth", [])),
        "hotness_delta": diff.get("hotness_delta", 0),
    }, ensure_ascii=False))
    return 0


# ──────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Research landscape assessment helper")
    sub = parser.add_subparsers(dest="command", required=True)

    p_analyze = sub.add_parser("analyze", help="Build assessment snapshot")
    p_analyze.add_argument("--enriched", required=True, help="Path to enriched JSONL")
    p_analyze.add_argument("--local", default=None, help="Path to local corpus JSON")
    p_analyze.add_argument("--topic", required=True, help="Topic name")
    p_analyze.add_argument("--months", type=int, default=6, help="Time window in months")
    p_analyze.add_argument("--output", required=True, help="Snapshot output path")

    p_diff = sub.add_parser("diff", help="Compare two snapshots")
    p_diff.add_argument("--previous", required=True, help="Previous snapshot JSON")
    p_diff.add_argument("--current", required=True, help="Current snapshot JSON")
    p_diff.add_argument("--output", required=True, help="Diff output path")

    args = parser.parse_args()
    if args.command == "analyze":
        return cmd_analyze(args)
    elif args.command == "diff":
        return cmd_diff(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
