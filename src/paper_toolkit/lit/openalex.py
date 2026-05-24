"""OpenAlex search + DOI fetch via the public JSON API.

OpenAlex returns dense, well-typed metadata and is the only one of the
three sources that ships an inverted-index abstract — we reconstruct it
back into running text for the BibTeX `abstract` field.
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

_BASE_URL = "https://api.openalex.org/works"

_TYPE_MAP: dict[str, EntryType] = {
    "journal-article": "article",
    "proceedings-article": "inproceedings",
    "book-chapter": "incollection",
    "book": "book",
    "monograph": "book",
    "report": "techreport",
    "dissertation": "phdthesis",
}


def _reconstruct_abstract(inverted: dict[str, list[int]] | None) -> str | None:
    if not inverted:
        return None
    positions: list[tuple[int, str]] = []
    for word, indices in inverted.items():
        for idx in indices:
            positions.append((idx, word))
    if not positions:
        return None
    positions.sort()
    return " ".join(word for _, word in positions)


def _flatten_author(authorship: dict[str, Any]) -> str:
    author = authorship.get("author") or {}
    return (author.get("display_name") or "").strip()


def _strip_doi_prefix(doi: str | None) -> str | None:
    if not doi:
        return None
    text = doi.strip()
    if text.lower().startswith("https://doi.org/"):
        return text[len("https://doi.org/") :]
    if text.lower().startswith("http://doi.org/"):
        return text[len("http://doi.org/") :]
    return text


def parse_work(item: dict[str, Any]) -> LiteratureEntry:
    title = (item.get("title") or item.get("display_name") or "(untitled)").strip()
    doi = _strip_doi_prefix(item.get("doi"))
    year = item.get("publication_year")
    if not isinstance(year, int):
        try:
            year = int(year) if year is not None else None
        except (TypeError, ValueError):
            year = None
    venue: str | None = None
    primary_location = item.get("primary_location") or {}
    if primary_location:
        source = primary_location.get("source") or {}
        venue = (source.get("display_name") or "").strip() or None
    if not venue:
        host_venue = item.get("host_venue") or {}
        venue = (host_venue.get("display_name") or "").strip() or None
    authors = [name for name in (_flatten_author(a) for a in item.get("authorships") or []) if name]
    entry_type = _TYPE_MAP.get(item.get("type", ""), "misc")
    abstract = _reconstruct_abstract(item.get("abstract_inverted_index"))
    openalex_id = (item.get("id") or "").strip()
    url = doi and f"https://doi.org/{doi}"
    cite_key = make_cite_key(authors=authors, year=year, title=title)
    return LiteratureEntry(
        source="openalex",
        source_id=openalex_id or doi or cite_key,
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
        "search": query,
        "per_page": str(max(1, min(limit, 200))),
    }
    filters: list[str] = []
    if year_from is not None:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to is not None:
        filters.append(f"to_publication_date:{year_to}-12-31")
    if filters:
        params["filter"] = ",".join(filters)
    return add_mailto_param(f"{_BASE_URL}?{urllib.parse.urlencode(params)}")


def search_openalex(
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
        raise HttpError(f"OpenAlex returned HTTP {response.status} for {url}")
    payload = json.loads(response.text)
    results = payload.get("results") or []
    return [parse_work(item) for item in results]


def fetch_openalex_doi(*, doi: str, client: HttpClient | None = None) -> LiteratureEntry:
    sanitized = doi.strip().lstrip("/")
    url = add_mailto_param(f"{_BASE_URL}/https://doi.org/{urllib.parse.quote(sanitized, safe='/')}")
    response = polite_get(url, accept="application/json", client=client)
    if response.status != 200:
        raise HttpError(f"OpenAlex returned HTTP {response.status} for DOI {doi}")
    payload = json.loads(response.text)
    return parse_work(payload)
