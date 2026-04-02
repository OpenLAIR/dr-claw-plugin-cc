#!/usr/bin/env python3
"""
Strong LaTeX/BibTeX reference audit for AI research repos.

Checks:
1) Missing citation keys per LaTeX root project
2) Missing bibliography files
3) Malformed BibTeX entries and duplicate keys
4) Formatting/metadata risks (missing required fields, invalid DOI/arXiv IDs, future years)
5) Potentially fabricated references (Crossref/OpenAlex/arXiv checks; no Semantic Scholar)
"""

from __future__ import annotations

import argparse
import bisect
import collections
import dataclasses
import datetime as dt
import difflib
import json
import pathlib
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


CITE_RE = re.compile(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*)*\{([^}]+)\}")
INCLUDE_RE = re.compile(r"\\(input|include)\s*\{([^}]+)\}")
BIB_RE = re.compile(r"\\bibliography\s*\{([^}]+)\}")
ADDBIB_RE = re.compile(r"\\addbibresource(?:\[[^\]]*\])?\s*\{([^}]+)\}")
DOC_RE = re.compile(r"\\documentclass")
ENTRY_RE = re.compile(r"@\s*([A-Za-z]+)\s*([({])")
DOI_RE = re.compile(r"^10\.\d{4,9}/[-._;()/:A-Z0-9]+$", re.IGNORECASE)
ARXIV_NEW_RE = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
ARXIV_OLD_RE = re.compile(r"^[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(v\d+)?$", re.IGNORECASE)
URL_RE = re.compile(r"^https?://", re.IGNORECASE)
INSECURE_SSL_CONTEXT = ssl._create_unverified_context()


@dataclasses.dataclass
class CiteOccurrence:
    key: str
    file: str
    line: int


@dataclasses.dataclass
class BibEntry:
    key: str
    entry_type: str
    file: str
    line: int
    fields_present: Set[str]
    title: Optional[str]
    year: Optional[int]
    doi: Optional[str]
    url: Optional[str]
    arxiv_id: Optional[str]
    has_author: bool
    has_venue: bool


@dataclasses.dataclass
class ProjectAudit:
    root: str
    tex_files: Set[str]
    bib_files: Set[str]
    citations: Dict[str, List[CiteOccurrence]]
    missing_bib_files: List[Dict[str, object]]
    missing_includes: List[Dict[str, object]]


def strip_tex_comment(line: str) -> str:
    out = []
    escaped = False
    for ch in line:
        if ch == "%" and not escaped:
            break
        out.append(ch)
        if ch == "\\" and not escaped:
            escaped = True
        else:
            escaped = False
    return "".join(out)


def line_indexer(text: str):
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)

    def line_of(pos: int) -> int:
        return bisect.bisect_right(starts, pos)

    return line_of


def normalize_title(title: Optional[str]) -> str:
    if not title:
        return ""
    t = title.lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def strip_latex_markup(text: Optional[str]) -> str:
    if not text:
        return ""
    t = text
    # Drop simple LaTeX commands while preserving text payload.
    t = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?", " ", t)
    t = t.replace("{", " ").replace("}", " ")
    t = t.replace("~", " ")
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def clean_field_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    v = value.strip()
    v = re.sub(r"\s+", " ", v)
    return v.strip()


def extract_field_value(field_blob: str, name: str) -> Optional[str]:
    m = re.search(rf"(?is)\b{re.escape(name)}\s*=", field_blob)
    if not m:
        return None
    i = m.end()
    n = len(field_blob)
    while i < n and field_blob[i].isspace():
        i += 1
    if i >= n:
        return None
    if field_blob[i] == "{":
        depth = 1
        i += 1
        start = i
        while i < n and depth > 0:
            if field_blob[i] == "{":
                depth += 1
            elif field_blob[i] == "}":
                depth -= 1
            i += 1
        return clean_field_value(field_blob[start : i - 1])
    if field_blob[i] == '"':
        i += 1
        start = i
        while i < n:
            if field_blob[i] == '"' and field_blob[i - 1] != "\\":
                break
            i += 1
        return clean_field_value(field_blob[start:i])
    start = i
    while i < n and field_blob[i] not in ",\n\r":
        i += 1
    return clean_field_value(field_blob[start:i])


def parse_year(value: Optional[str]) -> Optional[int]:
    if not value:
        return None
    m = re.search(r"\b(19|20)\d{2}\b", value)
    if not m:
        return None
    try:
        return int(m.group(0))
    except ValueError:
        return None


def extract_arxiv_id(
    eprint: Optional[str], doi: Optional[str], url: Optional[str], journal: Optional[str]
) -> Optional[str]:
    candidates = [eprint, doi, url, journal]
    for c in candidates:
        if not c:
            continue
        t = c.strip()
        t = t.replace("arXiv:", "")
        t = t.replace("arxiv:", "")
        if "arxiv.org/abs/" in t.lower():
            t = t.split("arxiv.org/abs/", 1)[1]
        if "10.48550/arXiv." in t:
            t = t.split("10.48550/arXiv.", 1)[1]
        t = t.strip().strip("{}").strip()
        m_new = re.search(r"\d{4}\.\d{4,5}(v\d+)?", t)
        if m_new:
            return m_new.group(0)
        m_old = re.search(r"[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(v\d+)?", t, re.IGNORECASE)
        if m_old:
            return m_old.group(0)
    return None


def valid_arxiv_id(arxiv_id: str) -> bool:
    return bool(ARXIV_NEW_RE.match(arxiv_id) or ARXIV_OLD_RE.match(arxiv_id))


def resolve_include(current_dir: pathlib.Path, token: str) -> Optional[pathlib.Path]:
    token = token.strip()
    if not token:
        return None
    candidates = [token]
    if not pathlib.Path(token).suffix:
        candidates.append(f"{token}.tex")
    for c in candidates:
        p = pathlib.Path(c)
        if not p.is_absolute():
            p = (current_dir / p).resolve()
        if p.exists() and p.is_file():
            return p
    return None


def resolve_bib_file(current_dir: pathlib.Path, root_dir: pathlib.Path, token: str) -> pathlib.Path:
    token = token.strip().strip("{}")
    if token.startswith("./"):
        token = token[2:]
    if token.endswith(".bib"):
        names = [token]
    else:
        names = [f"{token}.bib"]
    # TeX may resolve from current file dir or project root dir.
    for name in names:
        for base in (current_dir, root_dir):
            p = (base / name).resolve()
            if p.exists() and p.is_file():
                return p
    # Return best-effort expected path for reporting.
    return (current_dir / names[0]).resolve()


def collect_project(root_tex: pathlib.Path) -> ProjectAudit:
    root_tex = root_tex.resolve()
    root_dir = root_tex.parent
    queue: List[pathlib.Path] = [root_tex]
    visited: Set[pathlib.Path] = set()
    citations: Dict[str, List[CiteOccurrence]] = collections.defaultdict(list)
    bib_files: Set[pathlib.Path] = set()
    missing_bib_files: List[Dict[str, object]] = []
    missing_includes: List[Dict[str, object]] = []

    while queue:
        tex = queue.pop()
        if tex in visited:
            continue
        visited.add(tex)
        try:
            lines = tex.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue

        for line_no, line in enumerate(lines, start=1):
            cleaned = strip_tex_comment(line)

            for m in CITE_RE.finditer(cleaned):
                raw = m.group(1)
                keys = [k.strip() for k in raw.split(",") if k.strip()]
                for key in keys:
                    citations[key].append(CiteOccurrence(key=key, file=str(tex), line=line_no))

            for m in INCLUDE_RE.finditer(cleaned):
                token = m.group(2).strip()
                include_path = resolve_include(tex.parent, token)
                if include_path is None:
                    missing_includes.append(
                        {"file": str(tex), "line": line_no, "token": token}
                    )
                else:
                    queue.append(include_path)

            for m in BIB_RE.finditer(cleaned):
                tokens = [t.strip() for t in m.group(1).split(",") if t.strip()]
                for token in tokens:
                    p = resolve_bib_file(tex.parent, root_dir, token)
                    if p.exists():
                        bib_files.add(p)
                    else:
                        missing_bib_files.append(
                            {"file": str(tex), "line": line_no, "token": token, "resolved": str(p)}
                        )

            for m in ADDBIB_RE.finditer(cleaned):
                token = m.group(1).strip()
                p = resolve_bib_file(tex.parent, root_dir, token)
                if p.exists():
                    bib_files.add(p)
                else:
                    missing_bib_files.append(
                        {"file": str(tex), "line": line_no, "token": token, "resolved": str(p)}
                    )

    return ProjectAudit(
        root=str(root_tex),
        tex_files={str(p) for p in visited},
        bib_files={str(p) for p in bib_files},
        citations=citations,
        missing_bib_files=missing_bib_files,
        missing_includes=missing_includes,
    )


def parse_bib_file(path: pathlib.Path):
    entries: Dict[str, BibEntry] = {}
    duplicates: List[Dict[str, object]] = []
    malformed: List[Dict[str, object]] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as e:
        malformed.append({"file": str(path), "line": 1, "message": f"read error: {e}"})
        return entries, duplicates, malformed

    line_of = line_indexer(text)
    n = len(text)
    at_positions = [m.end() - 1 for m in re.finditer(r"(?m)^[ \t]*@", text)]
    for at in at_positions:
        m = ENTRY_RE.match(text, at)
        if not m:
            malformed.append(
                {
                    "file": str(path),
                    "line": line_of(at),
                    "message": "Malformed BibTeX entry start after '@'",
                }
            )
            continue

        entry_type = m.group(1).lower()
        open_delim = m.group(2)
        close_delim = "}" if open_delim == "{" else ")"
        body_start = m.end()

        depth = 1
        j = body_start
        while j < n and depth > 0:
            ch = text[j]
            if ch == open_delim:
                depth += 1
            elif ch == close_delim:
                depth -= 1
            j += 1

        if depth != 0:
            malformed.append(
                {
                    "file": str(path),
                    "line": line_of(at),
                    "message": "Unterminated BibTeX entry",
                }
            )
            continue

        body = text[body_start : j - 1]

        # Non-citable BibTeX control entries.
        if entry_type in {"comment", "preamble"}:
            continue
        if entry_type == "string":
            if not re.match(r"\s*[A-Za-z0-9_:\-]+\s*=", body):
                malformed.append(
                    {
                        "file": str(path),
                        "line": line_of(at),
                        "message": "Malformed @string definition",
                    }
                )
            continue

        comma = body.find(",")
        if comma < 0:
            malformed.append(
                {
                    "file": str(path),
                    "line": line_of(at),
                    "message": "Missing key/body separator comma",
                }
            )
            continue

        key = body[:comma].strip()
        if not key:
            malformed.append(
                {"file": str(path), "line": line_of(at), "message": "Empty BibTeX key"}
            )
            continue

        field_blob = body[comma + 1 :]
        fields_present = set(
            f.lower() for f in re.findall(r"(?i)\b([a-z][a-z0-9_-]*)\s*=", field_blob)
        )
        title = extract_field_value(field_blob, "title")
        year_raw = extract_field_value(field_blob, "year")
        year = parse_year(year_raw)
        doi = extract_field_value(field_blob, "doi")
        url = extract_field_value(field_blob, "url")
        eprint = extract_field_value(field_blob, "eprint")
        journal = extract_field_value(field_blob, "journal")
        arxiv_id = extract_arxiv_id(eprint, doi, url, journal)

        has_author = "author" in fields_present or "editor" in fields_present
        has_venue = ("booktitle" in fields_present) or ("journal" in fields_present)

        entry = BibEntry(
            key=key,
            entry_type=entry_type,
            file=str(path),
            line=line_of(at),
            fields_present=fields_present,
            title=title,
            year=year,
            doi=doi,
            url=url,
            arxiv_id=arxiv_id,
            has_author=has_author,
            has_venue=has_venue,
        )

        if key in entries:
            duplicates.append(
                {
                    "file": str(path),
                    "key": key,
                    "line_first": entries[key].line,
                    "line_second": entry.line,
                }
            )
        else:
            entries[key] = entry

    return entries, duplicates, malformed


def http_get_json(url: str, timeout: float = 8.0) -> Tuple[Optional[dict], Optional[int], Optional[str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-reference-audit/1.0"})
    last_err: Optional[str] = None
    for context in (None, INSECURE_SSL_CONTEXT):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                code = getattr(resp, "status", 200)
                data = resp.read().decode("utf-8", errors="replace")
                return json.loads(data), code, None
        except urllib.error.HTTPError as e:
            return None, e.code, str(e)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            last_err = msg
            if context is None and "CERTIFICATE_VERIFY_FAILED" in msg:
                continue
            break
    return None, None, last_err


def http_get_text(url: str, timeout: float = 8.0) -> Tuple[Optional[str], Optional[int], Optional[str]]:
    req = urllib.request.Request(url, headers={"User-Agent": "ai-reference-audit/1.0"})
    last_err: Optional[str] = None
    for context in (None, INSECURE_SSL_CONTEXT):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=context) as resp:
                code = getattr(resp, "status", 200)
                data = resp.read().decode("utf-8", errors="replace")
                return data, code, None
        except urllib.error.HTTPError as e:
            return None, e.code, str(e)
        except Exception as e:  # noqa: BLE001
            msg = str(e)
            last_err = msg
            if context is None and "CERTIFICATE_VERIFY_FAILED" in msg:
                continue
            break
    return None, None, last_err


def verify_entry_crossref(doi: str, cache: Dict[str, Tuple[str, str]]) -> Tuple[str, str]:
    if doi in cache:
        return cache[doi]
    q = urllib.parse.quote(doi, safe="")
    url = f"https://api.crossref.org/works/{q}"
    _, code, err = http_get_json(url)
    if code == 200:
        res = ("verified", "Crossref DOI found")
    elif code == 404:
        res = ("failed", "Crossref DOI not found")
    else:
        res = ("unknown", f"Crossref lookup inconclusive ({code or err})")
    cache[doi] = res
    return res


def verify_entry_arxiv(arxiv_id: str, cache: Dict[str, Tuple[str, str]]) -> Tuple[str, str]:
    if arxiv_id in cache:
        return cache[arxiv_id]
    q = urllib.parse.quote(arxiv_id, safe="")
    url = f"https://export.arxiv.org/api/query?search_query=id:{q}&start=0&max_results=1"
    text, code, err = http_get_text(url)
    if code != 200 or text is None:
        res = ("unknown", f"arXiv lookup inconclusive ({code or err})")
    elif "<opensearch:totalResults>1</opensearch:totalResults>" in text or "<entry>" in text:
        res = ("verified", "arXiv ID found")
    elif "<opensearch:totalResults>0</opensearch:totalResults>" in text:
        res = ("failed", "arXiv ID not found")
    else:
        res = ("unknown", "arXiv response could not be interpreted")
    cache[arxiv_id] = res
    return res


def verify_entry_openalex(
    title: str, year: Optional[int], cache: Dict[str, Tuple[str, str]]
) -> Tuple[str, str]:
    query_title = strip_latex_markup(title)
    key = normalize_title(query_title)
    if key in cache:
        return cache[key]
    q = urllib.parse.quote(query_title)
    url = (
        "https://api.openalex.org/works?"
        f"search={q}&per-page=5&select=display_name,publication_year"
    )
    data, code, err = http_get_json(url)
    if code != 200 or data is None:
        res = ("unknown", f"OpenAlex lookup inconclusive ({code or err})")
        cache[key] = res
        return res
    results = data.get("results", []) if isinstance(data, dict) else []
    if not results:
        res = ("failed", "OpenAlex returned no candidate records")
        cache[key] = res
        return res

    target = normalize_title(query_title)
    best_ratio = 0.0
    best_year = None
    for r in results:
        cand_title = normalize_title(r.get("display_name", ""))
        ratio = difflib.SequenceMatcher(a=target, b=cand_title).ratio()
        cand_year = r.get("publication_year")
        if ratio > best_ratio:
            best_ratio = ratio
            best_year = cand_year

    if best_ratio >= 0.90 and (
        year is None or best_year is None or abs(int(best_year) - int(year)) <= 1
    ):
        res = ("verified", f"OpenAlex title match (score={best_ratio:.2f})")
    elif best_ratio < 0.55:
        res = ("failed", f"OpenAlex title mismatch (best score={best_ratio:.2f})")
    else:
        res = ("unknown", f"OpenAlex weak match (score={best_ratio:.2f})")
    cache[key] = res
    return res


def choose_bib_entry_for_key(
    key: str, bib_files: Sequence[str], parsed_by_file: Dict[str, Dict[str, BibEntry]]
) -> Optional[BibEntry]:
    for bib in bib_files:
        entries = parsed_by_file.get(bib, {})
        if key in entries:
            return entries[key]
    return None


def run_audit(repo_root: pathlib.Path, verify_limit: int, network: bool) -> dict:
    repo_root = repo_root.resolve()
    tex_files = sorted(repo_root.rglob("*.tex"))
    bib_files_all = sorted(repo_root.rglob("*.bib"))
    roots = [p for p in tex_files if DOC_RE.search(p.read_text(encoding="utf-8", errors="ignore"))]

    projects: List[ProjectAudit] = [collect_project(r) for r in roots]

    parsed_by_file: Dict[str, Dict[str, BibEntry]] = {}
    duplicates: List[Dict[str, object]] = []
    malformed: List[Dict[str, object]] = []
    global_key_index: Dict[str, List[Tuple[str, int]]] = collections.defaultdict(list)
    for bib in bib_files_all:
        entries, dups, bad = parse_bib_file(bib)
        parsed_by_file[str(bib.resolve())] = entries
        duplicates.extend(dups)
        malformed.extend(bad)
        for key, entry in entries.items():
            global_key_index[key].append((entry.file, entry.line))

    # Cross-file duplicate keys (same key defined in multiple files)
    cross_file_dupes = []
    for key, locations in global_key_index.items():
        files = sorted({f for f, _ in locations})
        if len(files) > 1:
            cross_file_dupes.append({"key": key, "files": files})

    missing_keys = []
    cite_count_total = 0
    for project in projects:
        project_bibs = sorted(set(project.bib_files))
        key_pool: Set[str] = set()
        lower_map: Dict[str, List[str]] = collections.defaultdict(list)
        for bib in project_bibs:
            for key in parsed_by_file.get(bib, {}).keys():
                key_pool.add(key)
                lower_map[key.lower()].append(key)
        for key, occs in project.citations.items():
            cite_count_total += len(occs)
            if key not in key_pool:
                suggestion = lower_map.get(key.lower(), [])
                missing_keys.append(
                    {
                        "root": project.root,
                        "key": key,
                        "occurrences": [
                            {"file": o.file, "line": o.line} for o in occs[:4]
                        ],
                        "suggestion": suggestion[:3],
                    }
                )

    format_issues = []
    future_entries = []
    current_year = dt.date.today().year
    for bib_file, entries in parsed_by_file.items():
        for key, e in entries.items():
            if not e.title:
                format_issues.append(
                    {"severity": "critical", "type": "missing-title", "key": key, "file": e.file, "line": e.line}
                )
            if not e.has_author:
                format_issues.append(
                    {"severity": "critical", "type": "missing-author-or-editor", "key": key, "file": e.file, "line": e.line}
                )
            if e.year is None:
                format_issues.append(
                    {"severity": "critical", "type": "missing-or-unparsable-year", "key": key, "file": e.file, "line": e.line}
                )
            elif e.year > current_year:
                future_entries.append(
                    {"key": key, "year": e.year, "file": e.file, "line": e.line}
                )
            if e.entry_type in {"inproceedings", "article"} and not e.has_venue:
                format_issues.append(
                    {"severity": "warning", "type": "missing-venue", "key": key, "file": e.file, "line": e.line}
                )
            if e.doi and not DOI_RE.match(e.doi):
                format_issues.append(
                    {"severity": "warning", "type": "invalid-doi-format", "key": key, "file": e.file, "line": e.line, "value": e.doi}
                )
            if e.url and not URL_RE.match(e.url):
                format_issues.append(
                    {"severity": "warning", "type": "non-http-url", "key": key, "file": e.file, "line": e.line, "value": e.url}
                )
            if e.arxiv_id and not valid_arxiv_id(e.arxiv_id):
                format_issues.append(
                    {"severity": "warning", "type": "invalid-arxiv-id-format", "key": key, "file": e.file, "line": e.line, "value": e.arxiv_id}
                )

    # Potentially fabricated refs: prioritize cited keys with high-risk metadata.
    risk_candidates = []
    for project in projects:
        bib_order = sorted(project.bib_files)
        for key in project.citations.keys():
            entry = choose_bib_entry_for_key(key, bib_order, parsed_by_file)
            if not entry:
                continue
            risk = 0
            reasons = []
            if entry.year is None:
                risk += 2
                reasons.append("year missing/unparsable")
            elif entry.year >= current_year:
                risk += 1
                reasons.append(f"recent year={entry.year}")
            if not entry.doi and not entry.arxiv_id and not entry.url:
                risk += 2
                reasons.append("no DOI/arXiv/URL")
            if entry.doi and not DOI_RE.match(entry.doi):
                risk += 2
                reasons.append("invalid DOI format")
            if entry.arxiv_id and not valid_arxiv_id(entry.arxiv_id):
                risk += 2
                reasons.append("invalid arXiv format")
            if entry.entry_type in {"inproceedings", "article"} and not entry.has_venue:
                risk += 1
                reasons.append("missing venue")
            if entry.title and any(tok in entry.title.lower() for tok in ["todo", "tbd", "placeholder", "xxxx"]):
                risk += 3
                reasons.append("placeholder-like title token")
            if risk > 0:
                risk_candidates.append((risk, entry, reasons))

    # dedupe by (file,key)
    dedup = {}
    for risk, entry, reasons in risk_candidates:
        k = (entry.file, entry.key)
        if k not in dedup or risk > dedup[k][0]:
            dedup[k] = (risk, entry, reasons)
    risk_candidates = sorted(dedup.values(), key=lambda x: (-x[0], x[1].file, x[1].line))

    verification_results = []
    crossref_cache: Dict[str, Tuple[str, str]] = {}
    arxiv_cache: Dict[str, Tuple[str, str]] = {}
    openalex_cache: Dict[str, Tuple[str, str]] = {}

    for risk, entry, reasons in risk_candidates[:verify_limit]:
        status = "unverified"
        detail = "network verification skipped"
        method = "none"
        if network:
            if entry.doi and DOI_RE.match(entry.doi):
                method = "crossref"
                status, detail = verify_entry_crossref(entry.doi, crossref_cache)
            elif entry.arxiv_id and valid_arxiv_id(entry.arxiv_id):
                method = "arxiv"
                status, detail = verify_entry_arxiv(entry.arxiv_id, arxiv_cache)
            elif entry.title:
                method = "openalex-title"
                status, detail = verify_entry_openalex(entry.title, entry.year, openalex_cache)
        verification_results.append(
            {
                "risk": risk,
                "key": entry.key,
                "title": entry.title,
                "year": entry.year,
                "file": entry.file,
                "line": entry.line,
                "reasons": reasons,
                "method": method,
                "status": status,
                "detail": detail,
            }
        )

    potential_fabricated = []
    unverified_manual = []
    for r in verification_results:
        if r["status"] == "failed":
            if r["method"] in {"crossref", "arxiv"}:
                potential_fabricated.append(r)
            elif r["method"] == "openalex-title" and r["risk"] >= 3:
                potential_fabricated.append(r)
            else:
                unverified_manual.append(r)
        elif r["status"] in {"unknown", "unverified"}:
            unverified_manual.append(r)

    missing_bib_files = []
    missing_includes = []
    for project in projects:
        missing_bib_files.extend(project.missing_bib_files)
        missing_includes.extend(project.missing_includes)

    return {
        "summary": {
            "repo_root": str(repo_root),
            "tex_files": len(tex_files),
            "bib_files": len(bib_files_all),
            "root_tex_files": len(roots),
            "citations_found": sum(len(p.citations) for p in projects),
            "citation_occurrences": cite_count_total,
            "bib_entries_parsed": sum(len(v) for v in parsed_by_file.values()),
            "verify_limit": verify_limit,
            "network_enabled": network,
        },
        "projects": [
            {
                "root": p.root,
                "tex_files_scanned": len(p.tex_files),
                "bib_files_scanned": sorted(p.bib_files),
                "citation_keys": len(p.citations),
            }
            for p in projects
        ],
        "missing_bib_files": missing_bib_files,
        "missing_includes": missing_includes,
        "missing_keys": missing_keys,
        "malformed_bib_entries": malformed,
        "duplicate_keys_same_file": duplicates,
        "duplicate_keys_cross_file": cross_file_dupes,
        "format_issues": format_issues,
        "future_dated_entries": future_entries,
        "potential_fabricated": potential_fabricated,
        "unverified_manual_review": unverified_manual,
    }


def print_human_report(report: dict) -> None:
    s = report["summary"]
    print("Reference Audit Summary")
    print(
        f"- Repo: {s['repo_root']}\n"
        f"- TeX files: {s['tex_files']} | Bib files: {s['bib_files']} | Root TeX files: {s['root_tex_files']}\n"
        f"- Citation keys: {s['citations_found']} | Citation occurrences: {s['citation_occurrences']}\n"
        f"- Parsed BibTeX entries: {s['bib_entries_parsed']}\n"
        f"- Network verification: {'on' if s['network_enabled'] else 'off'} (limit={s['verify_limit']})"
    )
    print()

    def section(name: str, items: Sequence[dict], limit: int = 20) -> None:
        print(f"{name}: {len(items)}")
        for item in items[:limit]:
            print(f"  - {json.dumps(item, ensure_ascii=True)}")
        if len(items) > limit:
            print(f"  - ... {len(items) - limit} more")
        print()

    section("Critical/Missing keys", report["missing_keys"], limit=30)
    section("Critical/Missing bibliography files", report["missing_bib_files"], limit=20)
    section("Critical/Malformed BibTeX entries", report["malformed_bib_entries"], limit=30)
    section("Duplicate keys (same .bib file)", report["duplicate_keys_same_file"], limit=30)
    section("Formatting issues", report["format_issues"], limit=40)
    section("Future-dated entries", report["future_dated_entries"], limit=30)
    section("Potential AI-made-up references (failed verification)", report["potential_fabricated"], limit=40)
    section("Needs manual verification", report["unverified_manual_review"], limit=40)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a strong LaTeX/BibTeX reference audit.")
    parser.add_argument("--repo", default=".", help="Repository root to scan.")
    parser.add_argument("--verify-limit", type=int, default=120, help="Max risky entries to network-verify.")
    parser.add_argument(
        "--no-network",
        action="store_true",
        help="Disable Crossref/OpenAlex/arXiv verification.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report.")
    args = parser.parse_args(argv)

    report = run_audit(
        pathlib.Path(args.repo),
        verify_limit=max(0, args.verify_limit),
        network=not args.no_network,
    )
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print_human_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
