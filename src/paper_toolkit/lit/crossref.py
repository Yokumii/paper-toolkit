"""CrossRef search + DOI fetch via the public JSON REST API.

CrossRef returns rich publisher metadata. We map: `DOI` -> doi,
`title[0]` -> title, `author` -> authors, `issued.date-parts[0][0]` ->
year, `container-title[0]` -> venue, `type` -> entry_type (mapped to
BibTeX shapes), and `URL` -> url.
"""

from __future__ import annotations

import json
import urllib.parse
from typing import Any

from paper_toolkit.lit.citekey import make_cite_key
from paper_toolkit.lit.http_client import (
    HttpClient,
    HttpError,
    add_mailto_param,
    polite_get,
)
from paper_toolkit.lit.models import EntryType, LiteratureEntry

_BASE_URL = "https://api.crossref.org/works"

_TYPE_MAP: dict[str, EntryType] = {
    "journal-article": "article",
    "proceedings-article": "inproceedings",
    "book-chapter": "incollection",
    "book": "book",
    "monograph": "book",
    "edited-book": "book",
    "report": "techreport",
    "dissertation": "phdthesis",
}


def _flatten_author(author: dict[str, Any]) -> str:
    given = (author.get("given") or "").strip()
    family = (author.get("family") or "").strip()
    if given and family:
        return f"{given} {family}"
    return family or given or (author.get("name") or "").strip()


def _extract_year(item: dict[str, Any]) -> int | None:
    for field in ("issued", "published-print", "published-online", "created"):
        parts = (item.get(field) or {}).get("date-parts")
        if parts and parts[0]:
            try:
                return int(parts[0][0])
            except (TypeError, ValueError):
                continue
    return None


def _first(values: list[Any] | None) -> str:
    if not values:
        return ""
    raw = values[0]
    return str(raw).strip() if raw is not None else ""


def parse_work(item: dict[str, Any]) -> LiteratureEntry:
    title = _first(item.get("title")) or "(untitled)"
    doi = (item.get("DOI") or "").strip() or None
    authors = [_flatten_author(a) for a in (item.get("author") or []) if _flatten_author(a)]
    year = _extract_year(item)
    venue = _first(item.get("container-title")) or None
    entry_type = _TYPE_MAP.get(item.get("type", ""), "misc")
    url = (item.get("URL") or "").strip() or None
    abstract_raw = item.get("abstract")
    abstract: str | None = None
    if isinstance(abstract_raw, str) and abstract_raw.strip():
        # CrossRef abstracts arrive wrapped in JATS tags; strip the most common ones.
        abstract = (
            abstract_raw.replace("<jats:p>", "")
            .replace("</jats:p>", "")
            .replace("<jats:title>", "")
            .replace("</jats:title>", "")
            .strip()
        )
    cite_key = make_cite_key(authors=authors, year=year, title=title)
    return LiteratureEntry(
        source="crossref",
        source_id=doi or cite_key,
        title=title,
        authors=authors,
        year=year,
        venue=venue,
        doi=doi,
        url=url,
        abstract=abstract,
        entry_type=entry_type,
        cite_key=cite_key,
    )


def _build_search_url(
    *,
    query: str,
    limit: int,
    year_from: int | None,
    year_to: int | None,
) -> str:
    params: dict[str, str] = {
        "query": query,
        "rows": str(max(1, min(limit, 50))),
        "select": (
            "DOI,title,author,issued,published-print,"
            "published-online,container-title,type,URL,abstract"
        ),
    }
    filters: list[str] = []
    if year_from is not None:
        filters.append(f"from-pub-date:{year_from}")
    if year_to is not None:
        filters.append(f"until-pub-date:{year_to}")
    if filters:
        params["filter"] = ",".join(filters)
    return add_mailto_param(f"{_BASE_URL}?{urllib.parse.urlencode(params)}")


def search_crossref(
    *,
    query: str,
    limit: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
    client: HttpClient | None = None,
) -> list[LiteratureEntry]:
    url = _build_search_url(query=query, limit=limit, year_from=year_from, year_to=year_to)
    response = polite_get(url, accept="application/json", client=client)
    if response.status != 200:
        raise HttpError(f"CrossRef returned HTTP {response.status} for {url}")
    payload = json.loads(response.text)
    message = payload.get("message") or {}
    items = message.get("items") or []
    return [parse_work(item) for item in items]


def fetch_crossref_doi(*, doi: str, client: HttpClient | None = None) -> LiteratureEntry:
    sanitized = doi.strip().lstrip("/")
    url = add_mailto_param(f"{_BASE_URL}/{urllib.parse.quote(sanitized, safe='/')}")
    response = polite_get(url, accept="application/json", client=client)
    if response.status != 200:
        raise HttpError(f"CrossRef returned HTTP {response.status} for DOI {doi}")
    payload = json.loads(response.text)
    return parse_work(payload.get("message") or {})
