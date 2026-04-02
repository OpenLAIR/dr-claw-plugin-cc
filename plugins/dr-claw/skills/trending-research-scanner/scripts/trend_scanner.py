#!/usr/bin/env python3
"""Trend scanner CLI — search, enrich, and merge research papers across sources.

Stateless tool designed for agent-in-the-loop usage. The agent calls subcommands
iteratively, evaluates results, refines queries, and synthesizes a final report.

Subcommands:
  search   — Query a single source, return JSON array to stdout
  enrich   — Batch-enrich a JSONL file with citation/impact signals
  merge    — Dedupe and merge multiple JSON files
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

USER_AGENT = "trend-scanner/1.0 (mailto:local)"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

# ---------------------------------------------------------------------------
# Utility helpers (self-contained copies)
# ---------------------------------------------------------------------------

def fetch_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
    method: str = "GET",
    data: Optional[bytes] = None,
) -> Any:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    merged_headers = {"User-Agent": USER_AGENT}
    if headers:
        merged_headers.update(headers)
    req = urllib.request.Request(url, headers=merged_headers, method=method, data=data)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_text(
    url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30,
) -> str:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower()).strip()


def _date_months_ago(months: int) -> str:
    """Return ISO date string N months before today."""
    today = dt.date.today()
    year = today.year
    month = today.month - months
    while month < 1:
        month += 12
        year -= 1
    day = min(today.day, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _extract_github_urls(text: str) -> List[str]:
    """Extract GitHub repo URLs from text."""
    if not text:
        return []
    pattern = r"https?://github\.com/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"
    matches = re.findall(pattern, text)
    return [f"https://github.com/{m}" for m in set(matches)]


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


# ---------------------------------------------------------------------------
# Source: Semantic Scholar (S2) — bulk search sorted by citations
# ---------------------------------------------------------------------------

def _s2_fetch_with_retry(url: str, params: Dict[str, Any], max_retries: int = 3) -> Any:
    """Fetch from S2 API with exponential backoff on 429."""
    for attempt in range(max_retries):
        try:
            return fetch_json(url, params=params, timeout=60)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                _log(f"S2 rate limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    return None


def search_s2(query: str, months: int = 3, max_results: int = 50) -> List[Dict[str, Any]]:
    """Semantic Scholar paper search, sorted by citation count descending."""
    date_from = _date_months_ago(months)
    fields = (
        "paperId,title,abstract,authors,year,publicationDate,venue,"
        "citationCount,influentialCitationCount,tldr,externalIds,openAccessPdf"
    )
    data = None

    # Try regular search endpoint with sort
    try:
        params = {
            "query": query,
            "limit": min(max_results, 100),
            "fields": fields,
            "publicationDateOrYear": f"{date_from}:",
            "sort": "citationCount:desc",
        }
        data = _s2_fetch_with_retry(
            "https://api.semanticscholar.org/graph/v1/paper/search",
            params=params,
        )
    except Exception as e:
        _log(f"S2 search with sort failed: {e}")

    # Fallback: without sort parameter
    if data is None:
        try:
            params2 = {
                "query": query,
                "limit": min(max_results, 100),
                "fields": fields,
                "publicationDateOrYear": f"{date_from}:",
            }
            data = _s2_fetch_with_retry(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params=params2,
            )
        except Exception as e:
            _log(f"S2 search fallback also failed: {e}")
            return []

    papers: List[Dict[str, Any]] = []
    for p in data.get("data", []):
        authors = [a.get("name", "") for a in (p.get("authors") or [])]
        tldr = (p.get("tldr") or {}).get("text", "")
        arxiv_id = (p.get("externalIds") or {}).get("ArXiv", "")
        pdf_url = (p.get("openAccessPdf") or {}).get("url", "")
        url = pdf_url or (f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else
              f"https://www.semanticscholar.org/paper/{p.get('paperId', '')}")
        papers.append({
            "title": p.get("title", ""),
            "authors": [a for a in authors if a],
            "abstract": (p.get("abstract") or "")[:500],
            "published": p.get("publicationDate"),
            "year": p.get("year"),
            "venue": p.get("venue", ""),
            "url": url,
            "arxiv_id": arxiv_id,
            "s2_id": p.get("paperId", ""),
            "citation_count": p.get("citationCount", 0),
            "influential_citation_count": p.get("influentialCitationCount", 0),
            "tldr": tldr,
            "source": "s2",
        })
    return papers


# ---------------------------------------------------------------------------
# Source: OpenAlex — trending works sorted by citation count
# ---------------------------------------------------------------------------

def search_openalex(query: str, months: int = 3, max_results: int = 50) -> List[Dict[str, Any]]:
    """OpenAlex works search, sorted by cited_by_count descending."""
    date_from = _date_months_ago(months)
    params = {
        "search": query,
        "sort": "cited_by_count:desc",
        "filter": f"from_publication_date:{date_from}",
        "per_page": min(max_results, 200),
        "mailto": "trend-scanner@local",
    }
    data = fetch_json("https://api.openalex.org/works", params=params, timeout=30)
    papers: List[Dict[str, Any]] = []
    for w in data.get("results", []):
        authors = []
        for authorship in (w.get("authorships") or []):
            name = (authorship.get("author") or {}).get("display_name")
            if name:
                authors.append(name)
        # Reconstruct abstract from inverted index if needed
        abstract = ""
        if w.get("abstract_inverted_index"):
            try:
                inv = w["abstract_inverted_index"]
                word_positions = []
                for word, positions in inv.items():
                    for pos in positions:
                        word_positions.append((pos, word))
                word_positions.sort()
                abstract = " ".join(w for _, w in word_positions)[:500]
            except Exception:
                pass

        # FWCI (field-weighted citation impact)
        fwci = None
        if w.get("cited_by_percentile_year"):
            fwci = w["cited_by_percentile_year"].get("max")
        if w.get("fwci") is not None:
            fwci = w["fwci"]

        doi = w.get("doi", "")
        url = doi if doi else (w.get("id") or "")
        papers.append({
            "title": w.get("title", ""),
            "authors": authors,
            "abstract": abstract,
            "published": w.get("publication_date"),
            "year": w.get("publication_year"),
            "url": url,
            "cited_by_count": w.get("cited_by_count", 0),
            "fwci": fwci,
            "openalex_id": (w.get("id") or "").split("/")[-1],
            "source": "openalex",
        })
    return papers


# ---------------------------------------------------------------------------
# Source: Hugging Face Daily Papers — community buzz
# ---------------------------------------------------------------------------

def search_hf(query: str, months: int = 3, max_results: int = 30) -> List[Dict[str, Any]]:
    """Fetch HF daily papers across multiple weeks, filter by query."""
    headers = {}
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    all_papers: List[Dict[str, Any]] = []
    today = dt.date.today()
    # Scan week by week for the requested month range
    weeks_to_scan = months * 4 + 1
    seen_ids = set()

    for week_offset in range(weeks_to_scan):
        target = today - dt.timedelta(weeks=week_offset)
        # ISO week format
        iso_year, iso_week, _ = target.isocalendar()
        week_str = f"{iso_year}-W{iso_week:02d}"
        params: Dict[str, Any] = {"limit": 100, "p": 0, "sort": "trending", "week": week_str}
        try:
            data = fetch_json(
                "https://huggingface.co/api/daily_papers",
                params=params, headers=headers, timeout=20,
            )
        except Exception as e:
            _log(f"HF week {week_str} failed: {e}")
            continue

        for item in (data or []):
            paper = item.get("paper", {}) if isinstance(item, dict) else {}
            paper_id = paper.get("id", "")
            if paper_id in seen_ids:
                continue
            seen_ids.add(paper_id)
            title = paper.get("title") or item.get("title") or ""
            if not title:
                continue
            summary = (
                paper.get("ai_summary") or paper.get("summary")
                or item.get("summary") or ""
            )
            if query and query.lower() not in f"{title} {summary}".lower():
                continue
            authors = []
            for author in (paper.get("authors") or []):
                if isinstance(author, dict):
                    name = author.get("name") or (author.get("user") or {}).get("fullname")
                    if name:
                        authors.append(name)
                elif isinstance(author, str):
                    authors.append(author)
            upvotes = paper.get("upvotes") or item.get("upvotes") or 0
            url = f"https://huggingface.co/papers/{paper_id}" if paper_id else ""
            published = paper.get("publishedAt") or item.get("publishedAt")

            all_papers.append({
                "title": title,
                "authors": authors,
                "abstract": summary[:500] if summary else "",
                "published": published,
                "url": url,
                "arxiv_id": paper_id,
                "hf_upvotes": upvotes,
                "source": "hf",
            })
            if len(all_papers) >= max_results:
                break
        if len(all_papers) >= max_results:
            break

    # Sort by upvotes descending
    all_papers.sort(key=lambda p: p.get("hf_upvotes", 0), reverse=True)
    return all_papers[:max_results]


# ---------------------------------------------------------------------------
# Source: arXiv — recent papers by date
# ---------------------------------------------------------------------------

def search_arxiv(query: str, months: int = 3, max_results: int = 50) -> List[Dict[str, Any]]:
    """arXiv API search, sorted by submitted date descending."""
    params = {
        "search_query": query,
        "start": 0,
        "max_results": min(max_results, 200),
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    }
    xml_text = fetch_text("http://export.arxiv.org/api/query", params=params, timeout=30)
    root = ET.fromstring(xml_text)
    papers: List[Dict[str, Any]] = []
    cutoff = _date_months_ago(months)
    for entry in root.findall("atom:entry", ATOM_NS):
        published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
        if published and published[:10] < cutoff:
            continue
        title = entry.findtext("atom:title", default="", namespaces=ATOM_NS).strip()
        title = " ".join(title.split())  # collapse whitespace
        abstract = entry.findtext("atom:summary", default="", namespaces=ATOM_NS).strip()
        entry_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
        arxiv_id = entry_id.split("/abs/")[-1] if "/abs/" in entry_id else entry_id.split("/")[-1]
        # Strip version
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)
        authors = [
            a.findtext("atom:name", default="", namespaces=ATOM_NS)
            for a in entry.findall("atom:author", ATOM_NS)
        ]
        categories = []
        for cat in entry.findall("atom:category", ATOM_NS):
            term = cat.get("term", "")
            if term:
                categories.append(term)
        pdf_url = ""
        for link in entry.findall("atom:link", ATOM_NS):
            if link.get("type") == "application/pdf" or link.get("title") == "pdf":
                pdf_url = link.get("href", "")
                break
        papers.append({
            "title": title,
            "authors": [a for a in authors if a],
            "abstract": abstract[:500],
            "published": published,
            "url": pdf_url or entry_id,
            "arxiv_id": arxiv_id,
            "categories": categories,
            "source": "arxiv",
        })
    return papers


# ---------------------------------------------------------------------------
# Enrich pipeline
# ---------------------------------------------------------------------------

def _enrich_s2_batch(papers: List[Dict[str, Any]]) -> None:
    """Batch-enrich papers with S2 citation data via POST /paper/batch."""
    # Collect papers that need S2 enrichment
    to_enrich = []
    for p in papers:
        if p.get("citation_count") is not None and p.get("citation_count", 0) > 0:
            continue  # already has data
        arxiv_id = p.get("arxiv_id")
        s2_id = p.get("s2_id")
        if arxiv_id:
            to_enrich.append(("ARXIV:" + arxiv_id, p))
        elif s2_id:
            to_enrich.append((s2_id, p))

    if not to_enrich:
        return

    fields = "paperId,citationCount,influentialCitationCount,tldr,venue,externalIds,openAccessPdf"
    # Batch in chunks of 500 (S2 limit)
    chunk_size = 500
    for i in range(0, len(to_enrich), chunk_size):
        chunk = to_enrich[i:i + chunk_size]
        ids = [item[0] for item in chunk]
        paper_map = {item[0]: item[1] for item in chunk}
        try:
            body = json.dumps({"ids": ids}).encode("utf-8")
            result = fetch_json(
                f"https://api.semanticscholar.org/graph/v1/paper/batch?fields={fields}",
                method="POST",
                data=body,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            for entry in (result or []):
                if not entry:
                    continue
                # Match back by paperId or externalIds
                matched = None
                ext = (entry.get("externalIds") or {})
                arxiv = ext.get("ArXiv")
                if arxiv and f"ARXIV:{arxiv}" in paper_map:
                    matched = paper_map[f"ARXIV:{arxiv}"]
                elif entry.get("paperId") in paper_map:
                    matched = paper_map[entry["paperId"]]
                if not matched:
                    continue
                matched["citation_count"] = entry.get("citationCount", 0)
                matched["influential_citation_count"] = entry.get("influentialCitationCount", 0)
                if entry.get("tldr"):
                    matched.setdefault("tldr", (entry["tldr"] or {}).get("text", ""))
                if entry.get("venue"):
                    matched.setdefault("venue", entry["venue"])
                matched["s2_id"] = entry.get("paperId", "")
        except Exception as e:
            _log(f"S2 batch enrich failed for chunk: {e}")
        time.sleep(0.5)  # rate limit


def _enrich_openalex_match(papers: List[Dict[str, Any]]) -> None:
    """Title-match papers against OpenAlex to fill cited_by_count and fwci."""
    for p in papers:
        if p.get("cited_by_count") is not None and p.get("cited_by_count", 0) > 0:
            continue
        title = p.get("title", "")
        if not title:
            continue
        try:
            params = {
                "search": title,
                "per_page": 1,
                "mailto": "trend-scanner@local",
            }
            data = fetch_json("https://api.openalex.org/works", params=params, timeout=15)
            results = data.get("results", [])
            if not results:
                continue
            w = results[0]
            # Verify title match
            if normalize_title(w.get("title", "")) != normalize_title(title):
                continue
            p["cited_by_count"] = w.get("cited_by_count", 0)
            if w.get("fwci") is not None:
                p["fwci"] = w["fwci"]
            p.setdefault("openalex_id", (w.get("id") or "").split("/")[-1])
        except Exception as e:
            _log(f"OpenAlex match failed for '{title[:60]}': {e}")
        time.sleep(0.2)  # polite rate


def _enrich_github_stars(papers: List[Dict[str, Any]]) -> None:
    """Extract GitHub URLs from abstracts and fetch star counts via gh API."""
    for p in papers:
        if p.get("github_stars") is not None:
            continue
        urls = _extract_github_urls(p.get("abstract", "") + " " + p.get("url", ""))
        if not urls:
            continue
        repo_url = urls[0]
        # Extract owner/repo
        match = re.search(r"github\.com/([^/]+/[^/]+)", repo_url)
        if not match:
            continue
        repo = match.group(1).rstrip("/")
        try:
            result = subprocess.run(
                ["gh", "api", f"repos/{repo}", "--jq", ".stargazers_count"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip().isdigit():
                p["github_stars"] = int(result.stdout.strip())
                p["github_url"] = f"https://github.com/{repo}"
        except Exception:
            pass


def _compute_attention_scores(papers: List[Dict[str, Any]], months: int) -> None:
    """Compute attention_score for each paper."""
    for p in papers:
        score = 0.0

        # Citation velocity: citations / months, ×5, cap 30
        citations = p.get("citation_count") or p.get("cited_by_count") or 0
        age_months = max(months, 1)
        # Try to compute actual age from publication date
        pub = p.get("published")
        if pub:
            try:
                pub_date = dt.date.fromisoformat(pub[:10])
                delta = (dt.date.today() - pub_date).days / 30.0
                if delta > 0:
                    age_months = delta
            except Exception:
                pass
        cit_velocity = citations / max(age_months, 0.5)
        score += min(cit_velocity * 5, 30)

        # Influential citations ×3, cap 15
        inf_cit = p.get("influential_citation_count", 0) or 0
        score += min(inf_cit * 3, 15)

        # HF upvotes ×0.5, cap 15
        hf_up = p.get("hf_upvotes", 0) or 0
        score += min(hf_up * 0.5, 15)

        # GitHub stars velocity: stars / months ×2, cap 15
        gh_stars = p.get("github_stars", 0) or 0
        if gh_stars > 0:
            stars_velocity = gh_stars / max(age_months, 0.5)
            score += min(stars_velocity * 2, 15)

        # Conference tier bonus
        venue = (p.get("venue") or "").lower()
        if any(kw in venue for kw in ["oral", "spotlight", "best paper"]):
            score += 15
        elif any(kw in venue for kw in ["poster", "accepted", "neurips", "icml", "iclr", "aaai", "acl", "emnlp"]):
            score += 10

        # FWCI bonus, cap 10
        fwci = p.get("fwci")
        if fwci is not None and isinstance(fwci, (int, float)):
            score += min(fwci * 2, 10)

        p["attention_score"] = round(score, 1)


# ---------------------------------------------------------------------------
# Merge / Dedupe
# ---------------------------------------------------------------------------

def dedupe_and_merge(paper_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Deduplicate papers by normalized title, merging signals from different sources."""
    merged: Dict[str, Dict[str, Any]] = {}
    for papers in paper_lists:
        for paper in papers:
            title = paper.get("title", "")
            key = normalize_title(title)
            if not key:
                continue
            existing = merged.get(key)
            if not existing:
                paper["sources"] = [paper.get("source", "unknown")]
                merged[key] = paper
                continue
            # Merge sources
            sources = set(existing.get("sources", []))
            sources.add(paper.get("source", "unknown"))
            existing["sources"] = sorted(sources)
            # Merge signals — prefer non-zero / non-empty
            signal_fields = [
                "citation_count", "influential_citation_count", "cited_by_count",
                "fwci", "hf_upvotes", "github_stars", "github_url",
                "tldr", "venue", "arxiv_id", "s2_id", "openalex_id",
                "abstract", "categories", "attention_score",
            ]
            for field in signal_fields:
                new_val = paper.get(field)
                old_val = existing.get(field)
                if new_val and not old_val:
                    existing[field] = new_val
                elif isinstance(new_val, (int, float)) and isinstance(old_val, (int, float)):
                    if new_val > old_val:
                        existing[field] = new_val
            # Prefer longer author list
            if len(paper.get("authors", [])) > len(existing.get("authors", [])):
                existing["authors"] = paper["authors"]
    return list(merged.values())


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------

def cmd_search(args: argparse.Namespace) -> int:
    source = args.source
    query = args.query
    months = args.months
    max_results = args.max

    _log(f"Searching {source} for '{query}' (last {months} months, max {max_results})...")

    if source == "s2":
        papers = search_s2(query, months, max_results)
    elif source == "openalex":
        papers = search_openalex(query, months, max_results)
    elif source == "hf":
        papers = search_hf(query, months, max_results)
    elif source == "arxiv":
        papers = search_arxiv(query, months, max_results)
    else:
        _log(f"Unknown source: {source}")
        return 1

    _log(f"Found {len(papers)} papers from {source}")
    json.dump(papers, sys.stdout, indent=2, ensure_ascii=False)
    print()  # trailing newline
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    if not input_path.exists():
        _log(f"Input file not found: {input_path}")
        return 1

    # Read JSONL or JSON array
    papers: List[Dict[str, Any]] = []
    text = input_path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
        if isinstance(data, list):
            papers = data
        else:
            _log("Input must be a JSON array or JSONL")
            return 1
    except json.JSONDecodeError:
        # Try JSONL
        for line in text.strip().splitlines():
            line = line.strip()
            if line:
                papers.append(json.loads(line))

    _log(f"Enriching {len(papers)} papers...")

    # S2 batch
    _log("  S2 batch citation data...")
    _enrich_s2_batch(papers)

    # OpenAlex title-match
    _log("  OpenAlex title-match for cited_by_count/fwci...")
    _enrich_openalex_match(papers)

    # GitHub stars
    _log("  GitHub stars extraction...")
    _enrich_github_stars(papers)

    # Compute attention scores
    months = args.months or 3
    _log("  Computing attention scores...")
    _compute_attention_scores(papers, months)

    # Sort by attention score
    papers.sort(key=lambda p: p.get("attention_score", 0), reverse=True)

    # Output
    output_path = Path(args.output) if args.output else None
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for p in papers:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        _log(f"Wrote {len(papers)} enriched papers to {output_path}")
    else:
        json.dump(papers, sys.stdout, indent=2, ensure_ascii=False)
        print()

    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    all_lists: List[List[Dict[str, Any]]] = []
    for fpath in args.files:
        p = Path(fpath)
        if not p.exists():
            _log(f"File not found: {fpath}")
            continue
        text = p.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            if isinstance(data, list):
                all_lists.append(data)
            else:
                _log(f"Skipping {fpath}: not a JSON array")
        except json.JSONDecodeError:
            # Try JSONL
            papers = []
            for line in text.strip().splitlines():
                line = line.strip()
                if line:
                    try:
                        papers.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            if papers:
                all_lists.append(papers)

    if not all_lists:
        _log("No valid input files")
        return 1

    merged = dedupe_and_merge(all_lists)
    _log(f"Merged into {len(merged)} unique papers")

    output_path = Path(args.output) if args.output else None
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for p in merged:
                f.write(json.dumps(p, ensure_ascii=False) + "\n")
        _log(f"Wrote {len(merged)} papers to {output_path}")
    else:
        json.dump(merged, sys.stdout, indent=2, ensure_ascii=False)
        print()

    return 0


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trend scanner — search, enrich, merge research papers.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # -- search --
    p_search = sub.add_parser("search", help="Query a single source, return JSON to stdout")
    p_search.add_argument("--source", required=True, choices=["s2", "openalex", "hf", "arxiv"],
                          help="Data source to query")
    p_search.add_argument("--query", required=True, help="Search query string")
    p_search.add_argument("--months", type=int, default=3, help="Look-back window in months (default: 3)")
    p_search.add_argument("--max", type=int, default=50, help="Max results to return (default: 50)")

    # -- enrich --
    p_enrich = sub.add_parser("enrich", help="Batch-enrich papers with citation/impact signals")
    p_enrich.add_argument("input", help="Input file (JSON array or JSONL)")
    p_enrich.add_argument("--output", default=None, help="Output JSONL file (default: stdout)")
    p_enrich.add_argument("--months", type=int, default=3, help="Default age assumption for velocity calc")

    # -- merge --
    p_merge = sub.add_parser("merge", help="Dedupe and merge multiple JSON/JSONL files")
    p_merge.add_argument("files", nargs="+", help="Input JSON/JSONL files to merge")
    p_merge.add_argument("--output", default=None, help="Output JSONL file (default: stdout)")

    args = parser.parse_args()
    if args.command == "search":
        return cmd_search(args)
    elif args.command == "enrich":
        return cmd_enrich(args)
    elif args.command == "merge":
        return cmd_merge(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
