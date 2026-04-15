#!/usr/bin/env python3
"""Search AI/ML papers across multiple sources without MCP dependencies."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional

USER_AGENT = "searching-ai-papers/1.0 (mailto:local)"
ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}


def fetch_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    merged_headers = {"User-Agent": USER_AGENT}
    if headers:
        merged_headers.update(headers)
    req = urllib.request.Request(url, headers=merged_headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_text(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> str:
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", title.lower()).strip()


def trim(text: str, max_len: int = 180) -> str:
    text = " ".join(text.split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def extract_year(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1]
        return dt.datetime.fromisoformat(value).year
    except Exception:
        pass
    try:
        return int(value)
    except Exception:
        return None


def search_arxiv(query: str, max_results: int) -> List[Dict[str, Any]]:
    params = {
        "search_query": query,
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
    }
    xml_text = fetch_text("http://export.arxiv.org/api/query", params=params)
    root = ET.fromstring(xml_text)
    papers: List[Dict[str, Any]] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        entry_id = entry.findtext("atom:id", default="", namespaces=ATOM_NS)
        title = entry.findtext("atom:title", default="", namespaces=ATOM_NS)
        summary = entry.findtext("atom:summary", default="", namespaces=ATOM_NS)
        published = entry.findtext("atom:published", default="", namespaces=ATOM_NS)
        updated = entry.findtext("atom:updated", default="", namespaces=ATOM_NS)
        authors = [
            author.findtext("atom:name", default="", namespaces=ATOM_NS)
            for author in entry.findall("atom:author", ATOM_NS)
        ]
        pdf_url = ""
        for link in entry.findall("atom:link", ATOM_NS):
            if link.get("type") == "application/pdf" or link.get("title") == "pdf":
                pdf_url = link.get("href", "")
                break
        papers.append(
            {
                "id": entry_id.split("/")[-1],
                "title": title.strip(),
                "authors": [a for a in authors if a],
                "abstract": summary.strip(),
                "published": published,
                "updated": updated,
                "url": pdf_url or entry_id,
                "source": "arxiv",
            }
        )
    return papers


def search_semantic_scholar(query: str, max_results: int) -> List[Dict[str, Any]]:
    params = {
        "query": query,
        "limit": max_results,
        "fields": "paperId,title,abstract,authors,year,publicationDate,venue,url",
    }
    data = fetch_json("https://api.semanticscholar.org/graph/v1/paper/search", params=params)
    papers: List[Dict[str, Any]] = []
    for paper in data.get("data", []):
        authors = [a.get("name", "") for a in paper.get("authors", [])]
        papers.append(
            {
                "id": paper.get("paperId", ""),
                "title": paper.get("title", ""),
                "authors": [a for a in authors if a],
                "abstract": paper.get("abstract", ""),
                "published": paper.get("publicationDate"),
                "year": paper.get("year"),
                "venue": paper.get("venue"),
                "url": paper.get("url", ""),
                "source": "semantic_scholar",
            }
        )
    return papers


def search_openalex(query: str, max_results: int) -> List[Dict[str, Any]]:
    params = {
        "search": query,
        "per_page": max_results,
    }
    data = fetch_json("https://api.openalex.org/works", params=params)
    papers: List[Dict[str, Any]] = []
    for work in data.get("results", []):
        authors = []
        for authorship in work.get("authorships", []) or []:
            author = authorship.get("author", {})
            name = author.get("display_name")
            if name:
                authors.append(name)
        papers.append(
            {
                "id": (work.get("id", "").split("/")[-1]),
                "title": work.get("title", ""),
                "authors": authors,
                "abstract": work.get("abstract", "") or work.get("abstract_inverted_index", ""),
                "published": work.get("publication_date"),
                "year": work.get("publication_year"),
                "url": work.get("id", ""),
                "source": "openalex",
                "open_access": (work.get("open_access") or {}).get("is_oa", False),
                "type": work.get("type"),
            }
        )
    return papers


def _openreview_value(value: Any) -> Any:
    if isinstance(value, dict):
        return value.get("value")
    return value


def search_openreview(query: str, max_results: int, group: Optional[str]) -> List[Dict[str, Any]]:
    params = {"term": query, "limit": max_results}
    if group:
        params["group"] = group
    data = fetch_json("https://api2.openreview.net/notes/search", params=params)
    papers: List[Dict[str, Any]] = []
    for note in data.get("notes", []):
        content = note.get("content", {})
        title = _openreview_value(content.get("title"))
        abstract = _openreview_value(content.get("abstract"))
        authors = _openreview_value(content.get("authors"))
        keywords = _openreview_value(content.get("keywords"))
        if not title:
            continue
        # Heuristic: skip review-only notes lacking abstract/keywords/authors.
        if not any([abstract, keywords, authors]):
            continue
        if isinstance(authors, str):
            authors = [authors]
        forum = note.get("forum") or note.get("id")
        url = f"https://openreview.net/forum?id={forum}" if forum else ""
        cdate = note.get("cdate")
        published = None
        if isinstance(cdate, (int, float)):
            published = dt.datetime.utcfromtimestamp(cdate / 1000).isoformat()
        papers.append(
            {
                "id": note.get("id", ""),
                "title": title,
                "authors": authors or [],
                "abstract": abstract or "",
                "keywords": keywords or [],
                "published": published,
                "url": url,
                "source": "openreview",
            }
        )
    return papers


def search_openreview_iclr_accepted(year: int, max_results: int) -> List[Dict[str, Any]]:
    invitation = f"ICLR.cc/{year}/Conference/-/Submission"
    limit = 1000
    offset = 0
    accepted: List[Dict[str, Any]] = []

    def classify_venue(venue: str) -> Optional[str]:
        if not venue:
            return None
        if f"ICLR {year}" not in venue:
            return None
        lowered = venue.lower()
        if any(bad in lowered for bad in ["submitted", "withdrawn", "desk rejected", "rejected"]):
            return None
        if "conditional" in lowered:
            return "conditional_accept"
        if "spotlight" in lowered:
            return "spotlight"
        if "oral" in lowered:
            return "oral"
        if "poster" in lowered:
            return "poster"
        return "accept"

    while True:
        params = {"invitation": invitation, "limit": limit, "offset": offset}
        data = fetch_json("https://api2.openreview.net/notes", params=params)
        notes = data.get("notes", [])
        if not notes:
            break

        for note in notes:
            content = note.get("content", {})
            venue = _openreview_value(content.get("venue")) or ""
            decision = classify_venue(venue)
            if not decision:
                continue

            title = _openreview_value(content.get("title")) or ""
            if not title:
                continue
            abstract = _openreview_value(content.get("abstract")) or ""
            authors = _openreview_value(content.get("authors")) or []
            keywords = _openreview_value(content.get("keywords")) or []
            if isinstance(authors, str):
                authors = [authors]
            forum = note.get("forum") or note.get("id")
            url = f"https://openreview.net/forum?id={forum}" if forum else ""
            cdate = note.get("cdate")
            published = None
            if isinstance(cdate, (int, float)):
                published = dt.datetime.utcfromtimestamp(cdate / 1000).isoformat()

            accepted.append(
                {
                    "id": note.get("id", ""),
                    "title": title,
                    "authors": authors,
                    "abstract": abstract,
                    "keywords": keywords,
                    "published": published,
                    "url": url,
                    "source": "iclr_accepted",
                    "venue": venue,
                    "decision": decision,
                    "year": year,
                }
            )
            if max_results and len(accepted) >= max_results:
                return accepted

        offset += limit

    return accepted


def _matches_query(text: str, query: str) -> bool:
    if not query:
        return True
    return query.lower() in text.lower()


def search_hf_daily(
    query: str,
    max_results: int,
    date: Optional[str],
    week: Optional[str],
    month: Optional[str],
    sort: str,
    submitter: Optional[str],
) -> List[Dict[str, Any]]:
    params: Dict[str, Any] = {"limit": min(max_results, 100), "p": 0, "sort": sort}
    if date:
        params["date"] = date
    if week:
        params["week"] = week
    if month:
        params["month"] = month
    if submitter:
        params["submitter"] = submitter

    headers = {}
    hf_token = os.environ.get("HF_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    data = fetch_json("https://huggingface.co/api/daily_papers", params=params, headers=headers)
    papers: List[Dict[str, Any]] = []
    for item in data or []:
        paper = item.get("paper", {}) if isinstance(item, dict) else {}
        title = paper.get("title") or item.get("title") or ""
        if not title:
            continue
        summary = (
            paper.get("ai_summary")
            or paper.get("summary")
            or item.get("summary")
            or ""
        )
        if query and not _matches_query(f"{title} {summary}", query):
            continue

        authors = []
        for author in paper.get("authors", []) or []:
            if isinstance(author, dict):
                name = author.get("name") or (author.get("user") or {}).get("fullname")
                if name:
                    authors.append(name)
            elif isinstance(author, str):
                authors.append(author)

        paper_id = paper.get("id")
        url = f"https://huggingface.co/papers/{paper_id}" if paper_id else ""
        published = paper.get("publishedAt") or item.get("publishedAt")
        score = paper.get("upvotes")

        papers.append(
            {
                "id": paper_id or "",
                "title": title,
                "authors": authors,
                "abstract": summary,
                "published": published,
                "url": url,
                "source": "hf_daily",
                "score": score,
            }
        )
    return papers


def dedupe(papers: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    for paper in papers:
        title = paper.get("title") or ""
        key = normalize_title(title)
        if not key:
            continue
        existing = merged.get(key)
        sources = paper.get("sources") or [paper.get("source")]
        paper["sources"] = sorted(set([s for s in sources if s]))
        if not existing:
            merged[key] = paper
            continue
        # Merge fields into existing entry.
        existing_sources = set(existing.get("sources") or [])
        existing_sources.update(paper.get("sources") or [])
        existing["sources"] = sorted(existing_sources)
        for field in ["abstract", "url", "published", "year", "venue", "score"]:
            if not existing.get(field) and paper.get(field):
                existing[field] = paper[field]
        if paper.get("authors"):
            existing_authors = existing.get("authors") or []
            if len(existing_authors) < len(paper.get("authors")):
                existing["authors"] = paper.get("authors")
    return list(merged.values())


def filter_year(papers: Iterable[Dict[str, Any]], year_from: Optional[int], year_to: Optional[int]) -> List[Dict[str, Any]]:
    if year_from is None and year_to is None:
        return list(papers)
    filtered = []
    for paper in papers:
        year = paper.get("year") or extract_year(paper.get("published"))
        paper["year"] = year
        if year is None:
            continue
        if year_from is not None and year < year_from:
            continue
        if year_to is not None and year > year_to:
            continue
        filtered.append(paper)
    return filtered


def render_markdown(papers: List[Dict[str, Any]]) -> str:
    headers = ["Title", "Sources", "Year", "Score", "Authors", "URL"]

    def esc(text: str) -> str:
        return text.replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for paper in papers:
        title = esc(trim(paper.get("title", ""), 140))
        sources = esc(", ".join(paper.get("sources") or [paper.get("source", "")]))
        year = str(paper.get("year") or "")
        score = paper.get("score")
        score_text = str(score) if score is not None else ""
        authors = paper.get("authors") or []
        if isinstance(authors, str):
            authors = [authors]
        if len(authors) > 3:
            authors = authors[:3] + ["et al."]
        authors_text = esc(", ".join(authors))
        url = esc(paper.get("url", ""))
        lines.append(f"| {title} | {sources} | {year} | {score_text} | {authors_text} | {url} |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Search AI/ML papers across arXiv, Semantic Scholar, OpenAlex, and OpenReview.")
    parser.add_argument("--query", default="", help="Search query, e.g. 'graph neural networks interpretability'")
    parser.add_argument(
        "--sources",
        default="arxiv,semantic_scholar,openalex,openreview,hf_daily",
        help="Comma-separated sources (arxiv,semantic_scholar,openalex,openreview,hf_daily,iclr_accepted)",
    )
    parser.add_argument("--max-results", type=int, default=20, help="Max results per source")
    parser.add_argument("--year-from", type=int, default=None, help="Earliest publication year")
    parser.add_argument("--year-to", type=int, default=None, help="Latest publication year")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    parser.add_argument("--output", default=None, help="Write output to file path")
    parser.add_argument("--openreview-group", default=None, help="Optional OpenReview group filter (e.g., ICLR)")
    parser.add_argument("--iclr-year", type=int, default=None, help="ICLR year for accepted papers (e.g., 2025)")
    parser.add_argument("--hf-date", default=None, help="Hugging Face daily papers date (YYYY-MM-DD)")
    parser.add_argument("--hf-week", default=None, help="Hugging Face daily papers week (YYYY-Www)")
    parser.add_argument("--hf-month", default=None, help="Hugging Face daily papers month (YYYY-MM)")
    parser.add_argument(
        "--hf-sort",
        default="trending",
        choices=["trending", "publishedAt"],
        help="Hugging Face daily papers sort order",
    )
    parser.add_argument("--hf-submitter", default=None, help="Filter Hugging Face daily papers by submitter")
    parser.add_argument("--no-dedupe", action="store_true", help="Disable title-based deduplication")

    args = parser.parse_args()
    sources = [s.strip() for s in args.sources.split(",") if s.strip()]

    requires_query = {"arxiv", "semantic_scholar", "openalex", "openreview"}
    if not args.query and any(source in requires_query for source in sources):
        parser.error("Missing --query for sources that require a search term.")

    collected: List[Dict[str, Any]] = []
    for source in sources:
        if source == "arxiv":
            collected.extend(search_arxiv(args.query, args.max_results))
        elif source == "semantic_scholar":
            collected.extend(search_semantic_scholar(args.query, args.max_results))
        elif source == "openalex":
            collected.extend(search_openalex(args.query, args.max_results))
        elif source == "openreview":
            collected.extend(search_openreview(args.query, args.max_results, args.openreview_group))
        elif source == "hf_daily":
            collected.extend(
                search_hf_daily(
                    args.query,
                    args.max_results,
                    args.hf_date,
                    args.hf_week,
                    args.hf_month,
                    args.hf_sort,
                    args.hf_submitter,
                )
            )
        elif source == "iclr_accepted":
            if not args.iclr_year:
                parser.error("--iclr-year is required when using source iclr_accepted")
            collected.extend(search_openreview_iclr_accepted(args.iclr_year, args.max_results))
        else:
            print(f"Unknown source: {source}", file=sys.stderr)

    if args.no_dedupe:
        papers = collected
    else:
        papers = dedupe(collected)

    papers = filter_year(papers, args.year_from, args.year_to)
    for paper in papers:
        if not paper.get("year"):
            paper["year"] = extract_year(paper.get("published"))

    # Sort: prefer score when available, then year
    has_score = any(p.get("score") is not None for p in papers)
    if has_score:
        papers.sort(
            key=lambda p: (
                p.get("score") if p.get("score") is not None else -1,
                p.get("year") or 0,
                p.get("title") or "",
            ),
            reverse=True,
        )
    else:
        papers.sort(key=lambda p: (p.get("year") or 0, p.get("title") or ""), reverse=True)

    output: str
    if args.format == "json":
        output = json.dumps(papers, indent=2, ensure_ascii=False)
    else:
        output = render_markdown(papers)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
    else:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
